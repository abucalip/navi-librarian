"""Bounded cache warm-up for discovery paths (Server V2 Phase 7, carry-over "wiring").

Paths are built on demand and cached per (artist, kind, generation). This job builds the missing or stale
cache rows for every owned artist, so the first request from a client is a cache read. It reads only the
local knowledge store: no provider traffic, nothing written to Navidrome.

Bounds: ``max_seconds`` per run (default 300) through the job framework, plus the per-path limits of
:func:`intelligence.graph.paths.cached_path`. A run that stops with artists still missing goes back to
``queued`` and the next call resumes: artists whose cache is current are skipped without a rebuild, so a
resumed run does not repeat work. A path cut short by time is not saved, and the artist stays pending.

Triggered only by ``POST /api/knowledge/paths/warm``; there is no scheduler and no startup hook.
"""
from __future__ import annotations

import json
import sqlite3
import time
from typing import Callable, Sequence

from ..jobs import runner
from ..store import generations
from .paths import CACHE_PREFIX, PATH_KINDS, SLICE_RESOURCE, PathLimits, cached_path

JOB = "paths_warm"
DEFAULT_MAX_SECONDS = 300.0


def owned_artist_ids(db: sqlite3.Connection) -> list[int]:
    return [r["id"] for r in db.execute("SELECT id FROM entities WHERE type = 'artist' AND owned = 1 ORDER BY id")]


def _is_current(db: sqlite3.Connection, start_id: int, kind: str, gen: int, version: dict) -> bool:
    row = db.execute("SELECT payload FROM insights WHERE kind = ? AND subject_id = ? AND generation = ?",
                     (CACHE_PREFIX + kind, start_id, gen)).fetchone()
    return bool(row) and json.loads(row["payload"]).get("built_from") == version


def run_paths_warm(
    db: sqlite3.Connection,
    *,
    kinds: Sequence[str] = PATH_KINDS,
    max_seconds: float = DEFAULT_MAX_SECONDS,
    limits: PathLimits = PathLimits(),
    clock: Callable[[], float] = time.time,
) -> runner.RunResult:
    unknown = [k for k in kinds if k not in PATH_KINDS]
    if unknown:
        raise ValueError(f"unknown path kind: {unknown[0]!r}")

    def work(ctx: runner.JobContext) -> bool:
        ids = owned_artist_ids(db)
        gen = generations.current_generation(db)
        version = {SLICE_RESOURCE: generations.data_version(db, SLICE_RESOURCE)}
        built = skipped = empty = timed_out = 0
        todo = len(ids) * len(kinds)
        for kind in kinds:
            for start_id in ids:
                if _is_current(db, start_id, kind, gen, version):
                    skipped += 1
                    continue
                if not ctx.has_budget():
                    ctx.checkpoint({"built": built, "skipped": skipped, "empty": empty,
                                    "timed_out": timed_out, "pending": todo - built - skipped - empty})
                    return False
                path = cached_path(db, start_id, kind, limits=limits)
                if path is None:
                    empty += 1
                elif path["truncated"] == "time":
                    timed_out += 1  # not saved by cached_path; stays pending for a later run
                elif path["status"] == "empty":
                    empty += 1
                else:
                    built += 1
                ctx.checkpoint(items=1)
        ctx.checkpoint({"built": built, "skipped": skipped, "empty": empty, "timed_out": timed_out,
                        "pending": timed_out})
        return timed_out == 0

    return runner.run_job(db, JOB, work, max_seconds=max_seconds, clock=clock)
