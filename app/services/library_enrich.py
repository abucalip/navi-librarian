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
from intelligence.musicbrainz import auto_fill, update_requests
from intelligence.store import open_store
from intelligence.store import repositories as repo

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


def poll_once(librarian, db, should_stop=lambda: False):
    """One poll against an open store; returns the cycle summary. ``should_stop`` ends it early on shutdown."""
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
        should_stop=should_stop,
    )


def find_artist_id(librarian, db, mbid):
    """The Navidrome id of the library artist with this (lower-case) MusicBrainz id, or None.

    The store's artist entity usually carries the Navidrome id already (efficiency P5): one
    ``getArtist`` call confirms it still names this artist. Navidrome ids can change after a rescan,
    so a missing, changed or failing id falls back to reading the full ``getArtists`` index.
    """
    entity = repo.find_entity(db, "artist", mbid=mbid)
    known = entity.get("navidrome_id") if entity else None
    if known:
        try:
            artist = librarian.api_call("getArtist", id=known).get("artist") or {}
        except RuntimeError:   # Navidrome no longer knows this id
            artist = {}
        if str(artist.get("musicBrainzId") or "").lower() == mbid:
            return known
    for index in librarian.api_call("getArtists").get("artists", {}).get("index", []):
        for artist in librarian.items(index.get("artist")):
            if str(artist.get("musicBrainzId") or "").lower() == mbid:
                return artist.get("id")
    return None


def handle_requests(librarian, db, should_stop=lambda: False):
    """Process queued manual update requests (the "Request update" button); returns how many ran.

    ``should_stop`` is checked between requests, so shutdown never waits for the rest of the queue.
    """
    def find_artist(mbid):
        return find_artist_id(librarian, db, mbid)

    ran = 0
    while not should_stop() and update_requests.process_next(
        db,
        get_album=lambda album_id: librarian.api_call("getAlbum", id=album_id).get("album"),
        get_artist=lambda artist_id: librarian.api_call("getArtist", id=artist_id).get("artist"),
        find_artist=find_artist,
    ):
        ran += 1
    return ran


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
                    update_requests.recover_running(db)
                handle_requests(librarian, db, stop.is_set)
                summary = poll_once(librarian, db, stop.is_set)
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
