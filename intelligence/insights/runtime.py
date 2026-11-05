"""Runtime refresh for the Forgotten Gems lens (docs/ServerV2.md Phase 3).

Takes albums the caller already fetched from Navidrome (``getAlbumList2`` carries play count,
last played, star and rating), builds play records, and saves the gem cards through the job
runner so a repeat, a crash or a failure is visible in ``job_runs`` and never clears the previous
cards. No network, no provider traffic, no ownership or recommendation changes. An empty album
list is refused (a Navidrome outage must not wipe the saved cards); a library with sparse
history saves an empty list, as ``save_gems`` documents.

The provider-backed lenses (blind spots, series, hidden canon, anniversaries) are not refreshed
here: they need provider traffic the owner has not approved for runtime.
"""
from __future__ import annotations

import sqlite3
import time
from datetime import datetime
from typing import Any, Iterable, Mapping

from ..jobs import RunResult, run_job
from .forgotten_gems import GemsConfig, PlayRecord, find_forgotten_gems
from .persistence import dismissed_keys, save_gems

JOB = "insights_forgotten_gems"


class EmptyLibraryError(RuntimeError):
    """The album list was empty, so nothing is saved."""


def _epoch(value: Any) -> float | None:
    if not value or str(value).startswith("0001"):
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def album_to_record(album: Mapping[str, Any]) -> PlayRecord | None:
    """A Navidrome album object as a play record; None when it has no id."""
    album_id = album.get("id")
    if not album_id:
        return None
    rating = _int(album.get("userRating"))
    return PlayRecord(
        key=f"album:{album_id}", kind="album", title=str(album.get("name") or album.get("title") or ""),
        artist=album.get("artist"), play_count=_int(album.get("playCount")),
        last_played=_epoch(album.get("played")), starred=bool(album.get("starred")),
        rating=rating or None,
    )


def refresh_forgotten_gems(
    db: sqlite3.Connection, albums: Iterable[Mapping[str, Any]], *, now: float | None = None
) -> RunResult:
    """Recompute and save the gem cards from ``albums``; dismissed gems stay suppressed."""
    now = time.time() if now is None else now
    records = [r for r in (album_to_record(a) for a in albums) if r is not None]

    def work(ctx) -> bool:
        if not records:
            raise EmptyLibraryError("no albums")
        result = find_forgotten_gems(records, GemsConfig(now=now), dismissed=dismissed_keys(db))
        stored = save_gems(db, result, now=now)
        ctx.checkpoint({"albums": len(records), "records_with_history": result.records_with_history,
                        "cards": stored, "empty_reason": result.empty_reason})
        return True

    return run_job(db, JOB, work)
