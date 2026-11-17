"""Background refresh of the insights store (Server V2 Phase 3, efficiency R5).

Wiring only: the Navidrome album inventory comes through the injected librarian, the work is
``intelligence.insights.refresh_forgotten_gems`` and, for the provider-backed lenses,
``intelligence.insights.refresh_provider_lenses`` (its provider calls go through the shared gate and
the per-tick budget). The loop does nothing while no lens is listed in ``NAVI_INSIGHT_LENSES``, so a
server that has not switched a lens on never opens the store, reads the library or calls a provider.

A refresh runs at most once per ``CHECK_SECONDS``. The time of the last refresh that returned is kept
in the store's ``meta`` table, so a restart inside that window waits instead of reading the library
and spending the provider budget again. Setting the ``stop`` event ends a provider run before its next
request, and the loop returns at once.
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
from intelligence.insights.series_completion import CARD_KIND as SERIES_KIND
from intelligence.store import open_store

logger = logging.getLogger(__name__)

CHECK_SECONDS = 6 * 3600
LAST_RUN_KEY = "insights_refresh.last_run_at"
PROVIDER_LENSES = (BLIND_SPOT_KIND, CANON_KIND, ANNIVERSARY_KIND, SERIES_KIND)
PROVIDER_BUDGET = 120            # provider requests per tick (owner-approved slow trickle)
INGEST_ARTISTS_PER_TICK = 40     # Navidrome artists recorded per tick
INGEST_TTL_SECONDS = 7 * 86400.0
USER_AGENT = "Discair/1.0 (personal music discovery)"
_LOCK = threading.Lock()


def _ingest_step(librarian, db, stopping=lambda: False):
    """Record a slice of the owned library (Navidrome only), artists with an MBID, oldest first.

    Kept beside auto fill on purpose (efficiency P5): auto fill's first run only records the albums
    already in the library as its baseline and never ingests them, and it re-ingests a seen album only
    when it gains a release MBID. This step is what records those older albums and, every
    ``INGEST_TTL_SECONDS``, picks up later tag edits (track MBIDs, ISRCs) on albums already seen. It runs
    only while a provider lens is on and is bounded to ``INGEST_ARTISTS_PER_TICK`` artists per refresh.
    """
    now = time.time()
    root = librarian.api_call("getArtists")
    artists = [a for index in root.get("artists", {}).get("index", []) for a in librarian.items(index.get("artist"))]
    artists = [a for a in artists if a.get("musicBrainzId") and str(a.get("name", "")).strip().lower() != "various artists"]
    due = [a for a in artists if not provider_cache.is_fresh(provider_cache.get(db, "ingest", a["id"]), now, INGEST_TTL_SECONDS)]
    for artist in due[:INGEST_ARTISTS_PER_TICK]:
        if stopping():
            return
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


def refresh_once(librarian, environ=None, stop=None):
    """Refresh the enabled lenses once. Returns the run state, or None when nothing is enabled.

    With ``stop`` set, provider work is skipped or ends before its next request; the caller must then
    not record the refresh as done (``_loop`` checks this).
    """
    enabled = enabled_lenses(environ)
    gems = CARD_KIND in enabled
    providers = any(kind in enabled for kind in PROVIDER_LENSES)
    if not (gems or providers):
        return None
    stopping = stop.is_set if stop is not None else (lambda: False)
    states = {}
    with _LOCK:
        db = open_store(librarian.DATA_DIR / STORE_FILE)
        try:
            if gems:
                albums = fetch_album_inventory(librarian.api_call, librarian.items)
                states["forgotten_gem"] = refresh_forgotten_gems(db, albums).state
            if providers and not stopping():
                states["provider_lenses"] = refresh_provider_lenses(
                    db, get=_provider_get(librarian), headers={"User-Agent": USER_AGENT}, sleep=time.sleep,
                    ingest_step=lambda handle: _ingest_step(librarian, handle, stopping), budget=PROVIDER_BUDGET,
                    series=SERIES_KIND in enabled, should_stop=stopping,
                ).state
        finally:
            db.close()
    return states


def _lens_on(environ=None):
    enabled = enabled_lenses(environ)
    return any(kind in enabled for kind in (CARD_KIND, *PROVIDER_LENSES))


def _seconds_until_due(librarian, now, environ=None):
    """0 when a refresh is due now, or when no lens is on; otherwise the seconds to wait.

    The lens check comes first, so a server with no lens on never opens the store. A stored time in
    the future (the clock stepped back) counts as due, so the loop cannot freeze.
    """
    if not _lens_on(environ):
        return 0.0
    db = open_store(librarian.DATA_DIR / STORE_FILE)
    try:
        row = db.execute("SELECT value FROM meta WHERE key = ?", (LAST_RUN_KEY,)).fetchone()
    finally:
        db.close()
    if row is None:
        return 0.0      # never refreshed, including the first start after an upgrade
    try:
        elapsed = now - float(row["value"])
    except (TypeError, ValueError):
        return 0.0
    if not 0 <= elapsed < CHECK_SECONDS:
        return 0.0
    return CHECK_SECONDS - elapsed


def _record_run(librarian, now):
    db = open_store(librarian.DATA_DIR / STORE_FILE)
    try:
        with db:
            db.execute(
                "INSERT INTO meta (key, value) VALUES (?, ?) ON CONFLICT (key) DO UPDATE SET value = excluded.value",
                (LAST_RUN_KEY, str(float(now))),
            )
    finally:
        db.close()


def _loop(librarian, stop):
    while not stop.is_set():
        wait = CHECK_SECONDS
        try:
            due_in = _seconds_until_due(librarian, time.time())
            if due_in > 0:
                wait = due_in
            elif refresh_once(librarian, stop=stop) is not None and not stop.is_set():
                _record_run(librarian, time.time())   # a run cut short by shutdown stays due
        except Exception as exc:
            # Bounded diagnostics: the error type only.
            logger.error("Insights refresh failed (%s)", type(exc).__name__)
        stop.wait(wait)


def start(librarian, stop=None):
    stop = threading.Event() if stop is None else stop
    thread = threading.Thread(target=_loop, args=(librarian, stop), name="insights-refresh", daemon=True)
    thread.start()
    return thread
