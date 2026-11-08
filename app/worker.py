"""Dedicated background worker process (docs/efficiency.md A2, first job: automatic API fill).

Start with ``python -m app.worker``. It uses the same image, configuration and ``/data`` volume as the
web app and is the only process that writes the Server V2 knowledge store and calls MusicBrainz for it.
It runs until SIGTERM or SIGINT. This is deliberately the smallest worker: one job, no dispatcher yet;
further loops move here one at a time (efficiency.md A4).
"""
import logging
import signal
import threading

from app.api.dependencies import get_librarian
from app.services import library_enrich


def main(librarian=None, stop=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    stop = stop or threading.Event()
    if threading.current_thread() is threading.main_thread():
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, lambda *_: stop.set())
    library_enrich.run_forever(librarian or get_librarian(), stop)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
