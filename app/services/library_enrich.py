"""Loop that enriches newly added owned albums (Server V2, automatic API fill).

Runs only in the dedicated worker process (``python -m app.worker``): the worker is the single writer
of the knowledge store and the single MusicBrainz egress, the web process only reads (docs/ServerV2.md,
docs/efficiency.md A/E). The work is ``intelligence.musicbrainz.auto_fill.run_cycle``. On by default
(owner approved): polls every ``DEFAULT_POLL`` seconds; ``NAVI_AUTO_FILL_POLL_SECONDS`` changes the
interval and ``0`` or ``off`` switches it off. Each poll costs one ``getScanStatus`` call (about 300
bytes); Navidrome is read further, and MusicBrainz asked, only when the scan marker changed. A full
album inventory is read daily after midnight (server local time) as a safety net.
"""
import logging
import os
import threading

from app.api.insights import STORE_FILE
from discovery.library_snapshot import fetch_album_inventory
from intelligence.musicbrainz import auto_fill
from intelligence.store import open_store

logger = logging.getLogger(__name__)

POLL_ENV = "NAVI_AUTO_FILL_POLL_SECONDS"
MIN_POLL = 5.0
DEFAULT_POLL = 5.0
_LOCK = threading.Lock()


def poll_seconds(environ=None):
    """The configured poll interval (at least ``MIN_POLL``), or None when the loop is switched off (``0``, ``off`` or an unreadable value)."""
    raw = (environ if environ is not None else os.environ).get(POLL_ENV, "").strip().lower()
    if not raw:
        return DEFAULT_POLL
    try:
        value = float(raw)
    except ValueError:
        return None
    return max(value, MIN_POLL) if value > 0 else None


def poll_once(librarian, db):
    """One poll against an open store; returns the cycle summary."""
    def call(method, **params):
        return librarian.api_call(method, **params)

    def newest(offset, size):
        root = call("getAlbumList2", type="newest", size=size, offset=offset)
        return librarian.items(root.get("albumList2", {}).get("album"))

    return auto_fill.run_cycle(
        db,
        scan_status=lambda: call("getScanStatus").get("scanStatus", {}),
        newest=newest,
        full=lambda: fetch_album_inventory(librarian.api_call, librarian.items),
        get_album=lambda album_id: call("getAlbum", id=album_id).get("album"),
        get_artist=lambda artist_id: call("getArtist", id=artist_id).get("artist"),
    )


def run_forever(librarian, stop, environ=None):
    """Poll until ``stop`` (a ``threading.Event``) is set; returns at once when the loop is switched off."""
    interval = poll_seconds(environ)
    if interval is None:
        logger.info("Auto fill is switched off (%s)", POLL_ENV)
        return
    db = None
    last_error = None
    while not stop.is_set():
        try:
            with _LOCK:
                if db is None:
                    db = open_store(librarian.DATA_DIR / STORE_FILE)
                summary = poll_once(librarian, db)
            last_error = None
            if not summary.get("idle"):
                logger.info("Auto fill (%s): %s new, %s ingested, %s without MBID", summary.get("mode"),
                            summary.get("new"), summary.get("ingested"), summary.get("no_mbid"))
        except Exception as exc:
            if type(exc).__name__ != last_error:  # error type only, logged once per run of the same error
                logger.error("Auto fill failed (%s)", type(exc).__name__)
            last_error = type(exc).__name__
            if db is not None:
                db.close()
                db = None
        stop.wait(interval)
    if db is not None:
        db.close()
