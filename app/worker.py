"""Dedicated background worker process (docs/efficiency.md A2).

Start with ``python -m app.worker``. It uses the same image, configuration and ``/data`` volume as the
web app and is the only process that writes knowledge facts to the Server V2 store and calls MusicBrainz
for it (web routes write only owner records and caches; reads there are read-only). It runs until SIGTERM or SIGINT. Jobs owned here: the automatic API fill and the insights refresh
(Forgotten Gems and provider lenses, which write the knowledge store and call providers). The insights
refresh and the daily maintenance (job-history prune, R1, and the legacy metadata-cache prune of rows
older than 400 days, P3) are entries of the table-driven scheduler in ``app/worker_schedule.py``
(efficiency W1), which runs them one at a time and keeps their last runs in the store. Auto fill and the
runtime-metrics save keep their own threads: auto fill must stay responsive.

Exactly one worker runs: it takes an exclusive lock on ``DATA_DIR/worker.lock`` and exits non-zero if
another holds it. Holding the lock makes it safe to requeue ``running`` rows left by a killed worker.
On SIGTERM or SIGINT the loops stop; the worker waits up to ``SHUTDOWN_GRACE_SECONDS`` for them while it
still holds the lock (``stop_grace_period`` in compose.yaml is longer than that).
"""
import fcntl
import logging
import signal
import threading
import time

import metadata_cache
from app.api.insights import STORE_FILE
from app.api.dependencies import get_librarian
from app import worker_schedule
from app.services import insights_refresh, library_enrich, runtime_metrics
from intelligence.insights.provider_runtime import JOB as PROVIDER_LENSES_JOB
from intelligence.insights.runtime import JOB as FORGOTTEN_GEMS_JOB
from intelligence.jobs import prune_finished, recover_running
from intelligence.musicbrainz.api_fill import JOB as API_FILL_JOB
from intelligence.musicbrainz.job import JOB as SLICE_JOB
from intelligence.store import ensure_store, open_store
from intelligence.wikidata.ingest import JOB as WIKIDATA_JOB

logger = logging.getLogger(__name__)

LOCK_FILE = "worker.lock"
METRICS_SECONDS = 300            # how often the worker saves its runtime counters for the diagnostics route
SHUTDOWN_GRACE_SECONDS = 25      # below compose's stop_grace_period (30 s), so the process ends before Docker kills it
# The popularity job is named by string: the Phase 6 gate keeps taste imports out of app/ (a test pins the value).
POPULARITY_JOB = "taste_popularity"
# Jobs only the worker runs: a run left "running" belongs to a dead worker and is requeued at start.
WORKER_JOBS = (FORGOTTEN_GEMS_JOB, PROVIDER_LENSES_JOB, API_FILL_JOB, WIKIDATA_JOB, POPULARITY_JOB)
# Resuming a multi-gigabyte import needs an explicit decision, so an interrupted run is failed, not requeued.
FAIL_ON_RESTART_JOBS = (SLICE_JOB,)


def acquire_lock(data_dir):
    """Take the non-blocking exclusive worker lock; returns the open file (keep it open) or None if held."""
    handle = open(data_dir / LOCK_FILE, "a")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        return None
    return handle


def _maintain(data_dir, recover=False):
    db = open_store(data_dir / STORE_FILE)
    try:
        if recover:
            counts = recover_running(db, WORKER_JOBS, FAIL_ON_RESTART_JOBS)
            if any(counts.values()):
                logger.info("Recovered interrupted runs: %s requeued, %s failed", counts["requeued"], counts["failed"])
        prune_finished(db)
    finally:
        db.close()


def _prune_metadata_cache(librarian):
    """Drop legacy metadata-cache rows older than the cutoff (efficiency P3). No-op if the librarian has no cache."""
    cache = getattr(librarian, "_metadata_cache", None)
    if cache is None:
        return
    removed = cache.prune(metadata_cache.PRUNE_AFTER_SECONDS)
    logger.info("Metadata cache prune removed %s rows", removed)


def _daily_maintenance(librarian):
    # Each step is isolated: a failure in one is logged by type only and does not stop the other.
    try:
        _maintain(librarian.DATA_DIR)
    except Exception as exc:
        logger.error("Job history prune failed (%s)", type(exc).__name__)
    try:
        _prune_metadata_cache(librarian)
    except Exception as exc:
        logger.error("Metadata cache prune failed (%s)", type(exc).__name__)


def schedule_entries(librarian, stop):
    """The scheduler's entries, in the order they run when several are due at once."""
    return (
        worker_schedule.Entry("daily_maintenance", worker_schedule.daily(), lambda: _daily_maintenance(librarian)),
        worker_schedule.Entry("insights_refresh", insights_refresh.is_due,
                              lambda: insights_refresh.refresh_once(librarian, stop=stop),
                              legacy_key=insights_refresh.LAST_RUN_KEY),
    )


def _save_metrics(data_dir):
    try:
        db = open_store(data_dir / STORE_FILE)
        try:
            runtime_metrics.save_worker_snapshot(db)
        finally:
            db.close()
    except Exception as exc:
        logger.warning("Could not save runtime metrics (%s)", type(exc).__name__)


def _metrics_loop(data_dir, stop, every=METRICS_SECONDS):
    while not stop.wait(every):
        _save_metrics(data_dir)
    _save_metrics(data_dir)


def _wait_for_threads(threads, grace=SHUTDOWN_GRACE_SECONDS):
    """Join the loop threads against one shared deadline; log any still running (their work is requeued at start)."""
    deadline = time.monotonic() + grace
    for thread in threads:
        thread.join(max(0.0, deadline - time.monotonic()))
        if thread.is_alive():
            logger.error("Thread %s did not stop within %s s", thread.name, grace)


def main(librarian=None, stop=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    stop = stop or threading.Event()
    librarian = librarian or get_librarian()
    lock = acquire_lock(librarian.DATA_DIR)
    if lock is None:
        logger.error("Another worker holds %s; exiting", librarian.DATA_DIR / LOCK_FILE)
        return 1
    try:
        if threading.current_thread() is threading.main_thread():
            for sig in (signal.SIGTERM, signal.SIGINT):
                signal.signal(sig, lambda *_: stop.set())
        runtime_metrics.install()
        ensure_store(librarian.DATA_DIR / STORE_FILE)
        _maintain(librarian.DATA_DIR, recover=True)   # before any thread starts, so no run is live
        schedule_thread = worker_schedule.start(schedule_entries(librarian, stop),
                                                librarian.DATA_DIR / STORE_FILE, stop)
        # Auto fill runs on its own thread too: switching it off must not end the worker or the other jobs.
        enrich_thread = threading.Thread(target=library_enrich.run_forever, args=(librarian, stop),
                                         name="library-enrich", daemon=True)
        enrich_thread.start()
        metrics_thread = threading.Thread(target=_metrics_loop, args=(librarian.DATA_DIR, stop),
                                          name="runtime-metrics", daemon=True)
        metrics_thread.start()
        while not stop.wait(60):
            pass
        _wait_for_threads((schedule_thread, enrich_thread, metrics_thread))
        return 0
    finally:
        lock.close()


if __name__ == "__main__":
    raise SystemExit(main())
