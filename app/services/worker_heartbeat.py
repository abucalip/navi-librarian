"""Worker liveness heartbeat and its container healthcheck (efficiency C3).

The scheduler threads run jobs one at a time and the similar-artist precompute can run for hours, so a stamp
written between jobs would mark a healthy worker unhealthy. Instead a small thread rewrites a timestamp file under
the data directory every ``INTERVAL_SECONDS``, and only while every watched thread is alive: when a scheduler
thread dies the stamp stops advancing and the healthcheck fails once it is older than ``MAX_AGE_SECONDS``.
A file, not the SQLite store, so the stamp never contends with job writes.

Healthcheck: ``python -m app.services.worker_heartbeat`` exits 0 when the stamp is fresh, 1 otherwise.
"""
import os
import sys
import threading
import time
from pathlib import Path

HEARTBEAT_FILE = "worker.heartbeat"
INTERVAL_SECONDS = 30
MAX_AGE_SECONDS = 300


def write_stamp(data_dir, now=None):
    """Write the current time atomically (temp file, then rename)."""
    path = Path(data_dir) / HEARTBEAT_FILE
    tmp = path.with_name(HEARTBEAT_FILE + ".tmp")
    tmp.write_text(repr(time.time() if now is None else now))
    os.replace(tmp, path)


def is_fresh(data_dir, now=None, max_age=MAX_AGE_SECONDS):
    """True when the stamp exists, parses and is at most ``max_age`` seconds old (a future stamp is not fresh)."""
    try:
        stamped = float((Path(data_dir) / HEARTBEAT_FILE).read_text())
    except (OSError, ValueError):
        return False
    age = (time.time() if now is None else now) - stamped
    return 0 <= age <= max_age


def run(data_dir, threads, stop, every=INTERVAL_SECONDS):
    """Stamp now and every ``every`` seconds while all ``threads`` are alive; end when ``stop`` is set."""
    while not stop.is_set():
        if all(thread.is_alive() for thread in threads):
            try:
                write_stamp(data_dir)
            except OSError:
                pass   # a failed write only lets the stamp age, which is what the healthcheck reads
        stop.wait(every)


def start(data_dir, threads, stop, every=INTERVAL_SECONDS):
    """Start the heartbeat on its own daemon thread and return it."""
    thread = threading.Thread(target=run, args=(data_dir, threads, stop, every), name="worker-heartbeat", daemon=True)
    thread.start()
    return thread


def main():
    data_dir = os.environ.get("DISCAIR_DATA_DIR") or os.environ.get("NAVIDROME_LIBRARIAN_DATA_DIR") or "/data"
    return 0 if is_fresh(data_dir) else 1


if __name__ == "__main__":
    sys.exit(main())
