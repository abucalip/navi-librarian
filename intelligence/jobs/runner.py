"""Run a unit of background work so it is safe to repeat, stop and resume.

Properties, all on the ``job_runs`` table:

* **Duplicate-prevented:** at most one queued or running run per ``(job, scope)``
  (a unique index). Enqueueing twice returns the existing run.
* **Bounded:** a run may carry a ``max_items`` and/or ``max_seconds`` budget. The job
  checks ``ctx.has_budget()``; when the budget is spent the run stops cleanly.
* **Resumable:** a run that stopped early goes back to ``queued`` with its saved
  progress, and the next call continues from it. A run left ``running`` by a crash is
  put back by :func:`recover_stale`.
* **Visible state:** :func:`status`, :func:`list_runs` and :func:`last_good` read
  state, progress, timing and error text. Error text is clipped.
* **Last-known-good:** a failed or cancelled run never bumps the resource's
  ``data_version`` and never removes the previous run's results, so clients keep
  seeing the last successful output. Only a success bumps the version.

The wrapper does no network or provider work itself and never edits files.
"""
from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from typing import Any, Callable

from ..store.generations import bump_data_version, current_generation

ERROR_LIMIT = 500


@dataclass(frozen=True)
class RunResult:
    run_id: int | None
    state: str  # succeeded, failed, cancelled, queued (stopped early), skipped (already running)
    progress: dict[str, Any]
    error: str | None = None


class JobContext:
    """What a job function sees: saved progress, its budget, and a way to checkpoint."""

    def __init__(
        self,
        db: sqlite3.Connection,
        run_id: int,
        progress: dict[str, Any],
        clock: Callable[[], float],
        max_items: int | None,
        max_seconds: float | None,
    ):
        self._db, self.run_id, self.progress = db, run_id, progress
        self._clock = clock
        self._started = clock()
        self._max_items, self._max_seconds = max_items, max_seconds
        self.items_done = 0

    def checkpoint(self, progress: dict[str, Any] | None = None, items: int = 0) -> None:
        """Save progress and count ``items`` against the budget; commits at once."""
        if progress is not None:
            self.progress = progress
        self.items_done += items
        with self._db:
            self._db.execute(
                "UPDATE job_runs SET progress = ? WHERE id = ? AND state = 'running'",
                (_dump(self.progress), self.run_id),
            )

    def cancelled(self) -> bool:
        row = self._db.execute("SELECT state FROM job_runs WHERE id = ?", (self.run_id,)).fetchone()
        return row is None or row["state"] == "cancelled"

    def has_budget(self) -> bool:
        """False once cancelled or the item or time budget is spent: stop and return False."""
        if self.cancelled():
            return False
        if self._max_items is not None and self.items_done >= self._max_items:
            return False
        if self._max_seconds is not None and self._clock() - self._started >= self._max_seconds:
            return False
        return True


JobFunction = Callable[[JobContext], bool]


def enqueue(db: sqlite3.Connection, job: str, scope: str = "") -> tuple[int, bool]:
    """Queue a run; returns ``(run_id, created)``. An active run is returned, not duplicated."""
    _check_name(job)
    with db:
        row = _active(db, job, scope)
        if row:
            return row["id"], False
        cur = db.execute(
            "INSERT INTO job_runs (job, entity_scope, generation, state) VALUES (?, ?, ?, 'queued')",
            (job, scope, current_generation(db)),
        )
        return cur.lastrowid, True


def run_job(
    db: sqlite3.Connection,
    job: str,
    fn: JobFunction,
    *,
    scope: str = "",
    resource: str | None = None,
    max_items: int | None = None,
    max_seconds: float | None = None,
    clock: Callable[[], float] = time.time,
) -> RunResult:
    """Run ``fn`` once for ``(job, scope)``, resuming a queued run if there is one.

    ``fn`` returns True when all work is done and False when it stopped early (budget
    spent or cancelled). Raising marks the run failed. ``resource`` names the
    ``data_version`` counter to bump on success.
    """
    run_id, _ = enqueue(db, job, scope)
    with db:
        claimed = db.execute(
            "UPDATE job_runs SET state = 'running', started_at = COALESCE(started_at, ?), "
            "error = NULL WHERE id = ? AND state = 'queued'",
            (clock(), run_id),
        ).rowcount
    if not claimed:
        return RunResult(run_id, "skipped", _progress(db, run_id))
    ctx = JobContext(db, run_id, _progress(db, run_id), clock, max_items, max_seconds)
    try:
        finished = fn(ctx)
    except Exception as exc:  # the job failed; keep the previous good output untouched
        if ctx.cancelled():
            return RunResult(run_id, "cancelled", ctx.progress)
        return _finish(db, run_id, "failed", ctx.progress, clock(), error=_clip(exc))
    if ctx.cancelled():
        return _finish(db, run_id, "cancelled", ctx.progress, clock())
    if not finished:
        return _finish(db, run_id, "queued", ctx.progress, None)
    result = _finish(db, run_id, "succeeded", ctx.progress, clock())
    if resource:
        bump_data_version(db, resource)
    return result


def cancel(db: sqlite3.Connection, run_id: int, now: float | None = None) -> bool:
    """Cancel a queued or running run; a running job notices at its next budget check."""
    with db:
        return db.execute(
            "UPDATE job_runs SET state = 'cancelled', finished_at = ? "
            "WHERE id = ? AND state IN ('queued', 'running')",
            (time.time() if now is None else now, run_id),
        ).rowcount > 0


def recover_stale(db: sqlite3.Connection, now: float, older_than: float) -> int:
    """Return runs stuck in ``running`` since before ``now - older_than`` to ``queued``."""
    with db:
        return db.execute(
            "UPDATE job_runs SET state = 'queued' WHERE state = 'running' AND started_at < ?",
            (now - older_than,),
        ).rowcount


def status(db: sqlite3.Connection, job: str, scope: str = "") -> dict[str, Any] | None:
    """The newest run for a job and scope, or None."""
    row = db.execute(
        "SELECT * FROM job_runs WHERE job = ? AND entity_scope = ? ORDER BY id DESC LIMIT 1", (job, scope)
    ).fetchone()
    return _run(row) if row else None


def last_good(db: sqlite3.Connection, job: str, scope: str = "") -> dict[str, Any] | None:
    """The newest successful run: what clients are still being served after a failure."""
    row = db.execute(
        "SELECT * FROM job_runs WHERE job = ? AND entity_scope = ? AND state = 'succeeded' "
        "ORDER BY id DESC LIMIT 1", (job, scope)
    ).fetchone()
    return _run(row) if row else None


def list_runs(db: sqlite3.Connection, job: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    sql, args = "SELECT * FROM job_runs", []
    if job is not None:
        sql += " WHERE job = ?"
        args.append(job)
    rows = db.execute(sql + " ORDER BY id DESC LIMIT ?", (*args, max(1, limit))).fetchall()
    return [_run(r) for r in rows]


def prune_finished(db: sqlite3.Connection, keep: int = 20) -> int:
    """Delete old finished runs, keeping the newest ``keep`` per job and scope and every last-good run."""
    with db:
        return db.execute(
            """
            DELETE FROM job_runs WHERE state IN ('succeeded', 'failed', 'cancelled')
              AND id NOT IN (
                SELECT id FROM (
                  SELECT id, ROW_NUMBER() OVER (PARTITION BY job, entity_scope ORDER BY id DESC) AS n
                  FROM job_runs WHERE state IN ('succeeded', 'failed', 'cancelled')
                ) WHERE n <= ?
              )
              AND id NOT IN (
                SELECT MAX(id) FROM job_runs WHERE state = 'succeeded' GROUP BY job, entity_scope
              )
            """,
            (max(0, keep),),
        ).rowcount


# ---------------------------------------------------------------- helpers

def _finish(db, run_id, state, progress, finished_at, error=None) -> RunResult:
    with db:
        db.execute(
            "UPDATE job_runs SET state = ?, progress = ?, finished_at = ?, error = ? "
            "WHERE id = ? AND state = 'running'",
            (state, _dump(progress), finished_at, error, run_id),
        )
    return RunResult(run_id, state, progress, error)


def _active(db, job, scope):
    return db.execute(
        "SELECT id FROM job_runs WHERE job = ? AND entity_scope = ? AND state IN ('queued', 'running')",
        (job, scope),
    ).fetchone()


def _progress(db, run_id) -> dict[str, Any]:
    row = db.execute("SELECT progress FROM job_runs WHERE id = ?", (run_id,)).fetchone()
    return json.loads(row["progress"]) if row and row["progress"] else {}


def _run(row: sqlite3.Row) -> dict[str, Any]:
    d = dict(row)
    d["scope"] = d.pop("entity_scope")
    d["progress"] = json.loads(d["progress"]) if d["progress"] else {}
    return d


def _dump(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def _clip(exc: Exception) -> str:
    return f"{type(exc).__name__}: {exc}"[:ERROR_LIMIT]


def _check_name(job: str) -> None:
    if not job or job != job.strip():
        raise ValueError(f"invalid job name: {job!r}")
