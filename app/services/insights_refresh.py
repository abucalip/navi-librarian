"""Background refresh of the insights store (Server V2 Phase 3).

Wiring only: the Navidrome album inventory comes through the injected librarian, the work is
``intelligence.insights.refresh_forgotten_gems``. The loop does nothing while the Forgotten Gems
lens is not listed in ``NAVI_INSIGHT_LENSES``, so a server that has not switched a lens on never
opens the store or reads the library. Navidrome only; no provider traffic.
"""
import logging
import threading
import time

from app.api.insights import STORE_FILE, enabled_lenses
from discovery.library_snapshot import fetch_album_inventory
from intelligence.insights import refresh_forgotten_gems
from intelligence.insights.forgotten_gems import CARD_KIND
from intelligence.store import open_store

logger = logging.getLogger(__name__)

CHECK_SECONDS = 6 * 3600
_LOCK = threading.Lock()


def refresh_once(librarian, environ=None):
    """Refresh the enabled lenses once. Returns the run state, or None when nothing is enabled."""
    if CARD_KIND not in enabled_lenses(environ):
        return None
    with _LOCK:
        albums = fetch_album_inventory(librarian.api_call, librarian.items)
        db = open_store(librarian.DATA_DIR / STORE_FILE)
        try:
            return refresh_forgotten_gems(db, albums).state
        finally:
            db.close()


def _loop(librarian):
    while True:
        try:
            refresh_once(librarian)
        except Exception as exc:
            # Bounded diagnostics: the error type only.
            logger.error("Insights refresh failed (%s)", type(exc).__name__)
        time.sleep(CHECK_SECONDS)


def start(librarian):
    thread = threading.Thread(target=_loop, args=(librarian,), name="insights-refresh", daemon=True)
    thread.start()
    return thread
