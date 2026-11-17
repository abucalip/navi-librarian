"""One refresh per discovery list at a time, across the web and worker processes (efficiency W3).

The worker runs the scheduled list refreshes; the web runs manual and read-triggered ones. Each refresh of
one list goes through ``run_exclusive``, which wraps it in ``intelligence.jobs.run_job`` under job ``JOB``
with the list as scope, so the ``job_runs`` unique active index lets only one process refresh a list at a
time. A refresh that finds its list already running returns the caller's ``busy()`` answer (each caller
passes the one it already gave when its in-process lock was held) and runs nothing.

The refresh itself is unchanged: it runs on the calling thread with its own in-process lock, and its result
or exception is passed back as before. A run left ``running`` by a killed process is failed when its owning
process starts again (``recover_process``) or once it is older than ``STALE_AFTER_SECONDS``, so a crash
cannot block a list for good.

Without a usable knowledge store (the file is missing or not migrated) the refresh runs as before, guarded
by its in-process lock only, and the reason is logged once by error type. This module never creates a file.
"""
from __future__ import annotations

import logging
import sqlite3
import time
from pathlib import Path
from typing import Any, Callable

from intelligence.jobs import run_job
from intelligence.store import connect

logger = logging.getLogger(__name__)

JOB = "discovery_list_refresh"
STORE_FILE = "intelligence.sqlite3"     # the knowledge store, prepared by ``ensure_store`` at web and worker start
STALE_AFTER_SECONDS = 3 * 3600.0        # a run still "running" after this long belonged to a killed process
_process = "web"                        # which process this is; the worker sets "worker" at start
_warned = False


class _Refused:
    """A lock that is always held elsewhere: passing it gives a refresh function its existing busy answer."""

    def acquire(self, *_args, **_kwargs):
        return False

    def release(self):
        """Never reached: callers release only a lock they acquired."""


REFUSED = _Refused()


class _RefreshFailed(Exception):
    """Recorded in ``job_runs`` in place of the refresh's own error, which may carry provider details."""


def set_process(name: str) -> None:
    """Name this process ("web" or "worker") in the runs it starts, for ``recover_process``."""
    global _process
    _process = name


def _warn_once(reason: str) -> None:
    global _warned
    if not _warned:
        _warned = True
        logger.warning("Discovery list refreshes run without the cross-process guard (%s)", reason)


def _open(data_dir) -> sqlite3.Connection | None:
    if data_dir is None:
        return None
    path = Path(data_dir) / STORE_FILE
    if not path.is_file():
        _warn_once("no knowledge store")
        return None
    try:
        return connect(path)     # ``job_runs`` lives in the main file: no state attach, which would create one
    except Exception as exc:
        _warn_once(type(exc).__name__)
        return None


def _fail_stale(db: sqlite3.Connection, scope: str, now: float) -> int:
    with db:
        return db.execute(
            "UPDATE job_runs SET state = 'failed', finished_at = ?, error = 'stale run' "
            "WHERE job = ? AND entity_scope = ? AND state = 'running' AND started_at < ?",
            (now, JOB, scope, now - STALE_AFTER_SECONDS),
        ).rowcount


def recover_process(store_path, process: str, now: float | None = None) -> int:
    """Fail the list refreshes ``process`` left running when it stopped; call at that process's start.

    Safe because one web process and one worker (the worker lock) run at a time: at start, no run of
    this process is live. Runs of the other process and other jobs are untouched.
    """
    path = Path(store_path)
    if not path.is_file():
        return 0
    db = connect(path)
    try:
        with db:
            return db.execute(
                "UPDATE job_runs SET state = 'failed', finished_at = ?, error = 'interrupted by a restart' "
                "WHERE job = ? AND state = 'running' AND json_extract(progress, '$.process') = ?",
                (time.time() if now is None else now, JOB, process),
            ).rowcount
    finally:
        db.close()


def run_exclusive(data_dir, scope: str, run: Callable[[], Any], busy: Callable[[], Any],
                  clock: Callable[[], float] = time.time) -> Any:
    """Return ``run()`` unless a refresh of ``scope`` is already running in either process; then ``busy()``."""
    db = _open(data_dir)
    if db is None:
        return run()
    outcome: dict[str, Any] = {}

    def work(ctx) -> bool:
        ctx.checkpoint({"process": _process})
        try:
            outcome["result"] = run()
        except Exception as exc:
            outcome["error"] = exc
            raise _RefreshFailed(type(exc).__name__) from None
        return True     # the refresh ended (whatever it reported), so the run is finished

    try:
        _fail_stale(db, scope, clock())
        result = run_job(db, JOB, work, scope=scope, clock=clock)
    except sqlite3.IntegrityError:
        if not outcome:
            return busy()       # another process queued the same list between our check and insert
        result = None
    except Exception as exc:
        if not outcome:
            _warn_once(type(exc).__name__)
            return run()        # the store cannot take the run: refresh as before, under the in-process lock
        result = None
    finally:
        db.close()
    if result is not None and result.state == "skipped":
        return busy()
    if "error" in outcome:
        raise outcome["error"]
    return outcome.get("result")
