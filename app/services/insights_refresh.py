"""Background refresh of the insights store (Server V2 Phase 3).

Wiring only: the Navidrome album inventory comes through the injected librarian, the work is
``intelligence.insights.refresh_forgotten_gems``. The loop does nothing while the Forgotten Gems
lens is not listed in ``NAVI_INSIGHT_LENSES``, so a server that has not switched a lens on never
opens the store or reads the library. Navidrome only; no provider traffic.
"""
import logging
import threading
import time

import httpx

from app.api.insights import STORE_FILE, enabled_lenses
from discovery.library_snapshot import fetch_album_inventory
from intelligence.ingest.navidrome import ingest_album
from intelligence.insights import provider_cache, refresh_forgotten_gems, refresh_provider_lenses
from intelligence.insights.forgotten_gems import CARD_KIND
from intelligence.insights.anniversaries import CARD_KIND as ANNIVERSARY_KIND
from intelligence.insights.blind_spots import CARD_KIND as BLIND_SPOT_KIND
from intelligence.insights.hidden_canon import CARD_KIND as CANON_KIND
from intelligence.store import open_store

logger = logging.getLogger(__name__)

CHECK_SECONDS = 6 * 3600
PROVIDER_LENSES = (BLIND_SPOT_KIND, CANON_KIND, ANNIVERSARY_KIND)
PROVIDER_BUDGET = 120            # provider requests per tick (owner-approved slow trickle)
INGEST_ARTISTS_PER_TICK = 40     # Navidrome artists recorded per tick
INGEST_TTL_SECONDS = 7 * 86400.0
USER_AGENT = "Discair/1.0 (personal music discovery)"
_LOCK = threading.Lock()


def _ingest_step(librarian, db):
    """Record a slice of the owned library (Navidrome only), artists with an MBID, oldest first."""
    now = time.time()
    root = librarian.api_call("getArtists")
    artists = [a for index in root.get("artists", {}).get("index", []) for a in librarian.items(index.get("artist"))]
    artists = [a for a in artists if a.get("musicBrainzId") and str(a.get("name", "")).strip().lower() != "various artists"]
    due = [a for a in artists if not provider_cache.is_fresh(provider_cache.get(db, "ingest", a["id"]), now, INGEST_TTL_SECONDS)]
    for artist in due[:INGEST_ARTISTS_PER_TICK]:
        stubs = librarian.items(librarian.api_call("getArtist", id=artist["id"]).get("artist", {}).get("album"))
        for stub in stubs:
            album = librarian.api_call("getAlbum", id=stub["id"]).get("album")
            if album:
                album["artists"] = [{"id": artist["id"], "name": artist["name"], "musicBrainzId": artist["musicBrainzId"]}]
                ingest_album(db, album, now=now, search=None)
        provider_cache.put(db, "ingest", artist["id"], {}, now)


def _provider_get(librarian):
    """requests.get that adds the saved ListenBrainz token to ListenBrainz URLs only."""
    def get(url, **kwargs):
        if "listenbrainz" in url:
            token = str(librarian._discovery_settings_read().get("listenbrainz_token") or "")
            if token:
                kwargs["headers"] = {**kwargs.get("headers", {}), "Authorization": f"Token {token}"}
        return httpx.get(url, **kwargs)
    return get


def refresh_once(librarian, environ=None):
    """Refresh the enabled lenses once. Returns the run state, or None when nothing is enabled."""
    enabled = enabled_lenses(environ)
    gems = CARD_KIND in enabled
    providers = any(kind in enabled for kind in PROVIDER_LENSES)
    if not (gems or providers):
        return None
    states = {}
    with _LOCK:
        db = open_store(librarian.DATA_DIR / STORE_FILE)
        try:
            if gems:
                albums = fetch_album_inventory(librarian.api_call, librarian.items)
                states["forgotten_gem"] = refresh_forgotten_gems(db, albums).state
            if providers:
                states["provider_lenses"] = refresh_provider_lenses(
                    db, get=_provider_get(librarian), headers={"User-Agent": USER_AGENT}, sleep=time.sleep,
                    ingest_step=lambda handle: _ingest_step(librarian, handle), budget=PROVIDER_BUDGET,
                ).state
        finally:
            db.close()
    return states


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
