"""Dedicated background worker process (docs/efficiency.md A2).

Start with ``python -m app.worker``. It uses the same image, configuration and ``/data`` volume as the
web app and is the only process that writes knowledge facts to the Server V2 store and calls MusicBrainz
for it. It runs until SIGTERM or SIGINT. Jobs owned here: the automatic API fill and the insights refresh
(Forgotten Gems and provider lenses, which write the knowledge store and call providers). There is no
dispatcher yet; further loops move here one at a time (efficiency.md A4).

Exactly one worker runs: it takes an exclusive lock on ``DATA_DIR/worker.lock`` and exits non-zero if
another holds it. Holding the lock makes it safe to requeue ``running`` rows left by a killed worker.
"""
import fcntl
import logging
import signal
import threading

from app.api.insights import STORE_FILE
from app.api.dependencies import get_librarian
from app.services import insights_refresh, library_enrich
from intelligence.insights.provider_runtime import JOB as PROVIDER_LENSES_JOB
from intelligence.insights.runtime import JOB as FORGOTTEN_GEMS_JOB
from intelligence.jobs import prune_finished, recover_running
from intelligence.musicbrainz.api_fill import JOB as API_FILL_JOB
from intelligence.musicbrainz.job import JOB as SLICE_JOB
from intelligence.store import open_store
from intelligence.taste.popularity_job import JOB as POPULARITY_JOB
from intelligence.wikidata.ingest import JOB as WIKIDATA_JOB

logger = logging.getLogger(__name__)

LOCK_FILE = "worker.lock"
PRUNE_SECONDS = 24 * 3600
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
        _maintain(librarian.DATA_DIR, recover=True)   # before any thread starts, so no run is live
        insights_refresh.start(librarian)   # six-hourly loop on its own daemon thread, same process
        # Auto fill runs on its own thread too: switching it off must not end the worker or the other jobs.
        threading.Thread(target=library_enrich.run_forever, args=(librarian, stop), name="library-enrich",
                         daemon=True).start()
        while not stop.wait(PRUNE_SECONDS):
            try:
                _maintain(librarian.DATA_DIR)
            except Exception as exc:
                logger.error("Job history prune failed (%s)", type(exc).__name__)
        return 0
    finally:
        lock.close()


if __name__ == "__main__":
    raise SystemExit(main())
