"""Daily lens lists as a service (Engine 2, Phase 4, slices 3 and 4 wiring).

Lives outside ``navidrome_server.py`` (D-016). Each function takes the librarian object that
``app.api.dependencies.get_librarian`` returns and reads its helpers by attribute at call time,
the same adapter pattern the discovery routes use. The pure policy stays in
``discovery.lens_storage``, ``discovery.refresh.refresh_lens_lists`` and
``discovery.list_payload.build_lens_list_response``; this module only connects them to the
providers, the library and the store, and starts the daily refresh. Behind
``engine2_lens_lists_enabled`` (default off): nothing here reads the library or calls a provider
while the setting is off. See docs/engine2.md (Phase 4).
"""
from __future__ import annotations

import functools
import json
import logging
import os
import threading
import time
from collections.abc import Callable, Mapping
from datetime import datetime
from typing import Any

from discovery import history_fetch
from discovery import refresh as discovery_refresh
from discovery.lens_lists import LENS_LIST_ORDER, build_lens_lists, history_artist_mbids, usable_listens
from discovery.lens_storage import lens_day, lens_storage_name
from discovery.list_payload import build_lens_list_response, owned_predicate
from settings import service as settings_service

logger = logging.getLogger(__name__)

# Listening history read for the lens lists. Obsessions and Repeated tracks need more than the
# 30-day default; the page bound of the ListenBrainz client still applies.
DAILY_CHECK_SECONDS = 3600
MUSICBRAINZ_USER_AGENT = "NavidromeLibrarian/1.0 (personal music discovery)"
_REFRESH_LOCK = threading.Lock()


def lens_names() -> tuple[str, ...]:
    return tuple(lens.name for lens in LENS_LIST_ORDER)


def _owned_or_none(librarian: Any) -> Callable[[Any], bool] | None:
    """Ownership check against the current library, or None when the library cannot be read."""
    try:
        return owned_predicate(librarian._discovery_library_snapshot(), librarian._music_key)
    except Exception:
        return None


def list_response(librarian: Any, lens_name: str, count: int) -> str:
    """The JSON response for one stored lens list, with owned albums removed at read time.

    While ``engine2_lens_lists_enabled`` is off this answers with an empty, disabled response
    and reads neither the store nor the library.
    """
    if not settings_service.engine2_lens_lists_enabled_value(librarian._discovery_settings_read):
        return json.dumps({
            "list": lens_name,
            "generated_at": None,
            "items": [],
            "disabled": True,
            "message": "Lens lists are off. Set engine2_lens_lists_enabled to turn them on.",
        }, ensure_ascii=False, indent=2)
    cached = librarian._discovery_read_list(lens_storage_name(lens_name))
    return build_lens_list_response(lens_name, count, cached, _owned_or_none(librarian))


def _lastfm_username(settings_read: Callable[[], Mapping[str, Any]]) -> str:
    """The Last.fm account to read scrobbles from: the setting, else the LASTFM_USERNAME variable."""
    return str(settings_read().get("lastfm_username") or os.environ.get("LASTFM_USERNAME") or "").strip()


def _fetch_history(librarian: Any, settings_read: Callable[[], Mapping[str, Any]], lastfm_api_key: str) -> list[dict[str, Any]]:
    """Listening history for the lens lists, split between ListenBrainz and Last.fm.

    Both services hold the same listens, so windows alternate between them (see
    discovery.history_fetch). Last.fm is used only when both its key and account are configured.
    """
    import httpx
    from integrations.listenbrainz.client import request_headers as listenbrainz_headers

    sources = [("listenbrainz", functools.partial(
        history_fetch.listenbrainz_window, librarian._listenbrainz_username(),
        get=httpx.get, headers=listenbrainz_headers(),
    ))]
    lastfm_user = _lastfm_username(settings_read)
    if lastfm_api_key and lastfm_user:
        sources.append(("lastfm", functools.partial(
            history_fetch.lastfm_window, lastfm_user, lastfm_api_key, get=httpx.get,
        )))
    result = history_fetch.fetch_lens_history(sources, now=time.time())
    # Aggregate counts only: no listen, artist or album is logged.
    logger.info(
        "Lens history: %d listens in %d windows (%d unanswered), stopped: %s",
        len(result["listens"]), len(result["windows"]), result["unanswered"], result["stopped"],
    )
    return result["listens"]


def build(librarian: Any) -> dict[str, Any]:
    """Gather and build today's lens lists.

    Returns ``{"status": "disabled"}`` before any library or provider call when the setting is
    off, ``{"status": "failed", "reason": code}`` when gathering did not finish, or
    ``{"status": "built", "day": ..., "lists": {lens: payload}}``.
    """
    import httpx
    from discovery.candidate_gathering import RecommendationProviders
    from discovery.lens_pool_gatherer import gather_lens_pools
    from discovery.library_snapshot import fetch_album_inventory

    settings_read = librarian._discovery_settings_read
    if not settings_service.engine2_lens_lists_enabled_value(settings_read):
        return {"status": "disabled"}
    day = lens_day(datetime.now())
    providers = RecommendationProviders(
        listenbrainz_recent=librarian._listenbrainz_recent,
        listenbrainz_username=librarian._listenbrainz_username,
        music_key=librarian._music_key,
        metadata_cache_get=librarian._metadata_cache_get,
        metadata_cache_set=librarian._metadata_cache_set,
        is_album_candidate=librarian._discovery_is_album_candidate,
        api_call=librarian.api_call, items=librarian.items,
        http_get=httpx.get, http_client=httpx.Client, sleep=time.sleep, http_post=httpx.post,
        feedback_rows=librarian._discovery_feedback_rows,
    )
    listens = _fetch_history(librarian, settings_read, str(settings_read().get("lastfm_api_key") or ""))
    gathered = gather_lens_pools(
        listens, day=day, providers=providers,
        headers={"User-Agent": MUSICBRAINZ_USER_AGENT},
        lastfm_api_key=str(settings_read().get("lastfm_api_key") or ""),
        settings_read=settings_read,
    )
    if gathered.get("status") != "gathered":
        return {"status": "failed", "reason": ("gather_status_" + str(gathered.get("status")))[:40]}

    library_by_title: dict[str, list] = {}
    for album in fetch_album_inventory(librarian.api_call, librarian.items):
        title_key = librarian._music_key(album.get("name", ""))
        if title_key:
            library_by_title.setdefault(title_key, []).append(album)
    usable = usable_listens(listen for listen in listens if isinstance(listen, dict))
    lists = build_lens_lists(
        gathered["pools"], day=day, popularity=gathered["popularity"],
        artist_tags=gathered["artist_tags"], fallback_tags=gathered["fallback_tags"],
        library_by_title=library_by_title, known_artist_mbids=history_artist_mbids(usable),
        seeds=gathered["seeds"],
    )
    return {"status": "built", "day": day, "lists": lists}


def refresh(librarian: Any) -> dict[str, Any]:
    """Build the lens lists and store each one the snapshot policy accepts."""
    return discovery_refresh.refresh_lens_lists(
        lambda: build(librarian),
        librarian._discovery_read_list,
        librarian._discovery_write_list,
        _REFRESH_LOCK,
        excluded_provider=lambda: _owned_or_none(librarian),
    )


def _due(librarian: Any) -> bool:
    """True when the setting is on and any lens list is missing or not from today."""
    if not settings_service.engine2_lens_lists_enabled_value(librarian._discovery_settings_read):
        return False
    today = lens_day(datetime.now())
    for name in lens_names():
        cached = librarian._discovery_read_list(lens_storage_name(name))
        if not cached or (cached.get("payload") or {}).get("day") != today:
            return True
    return False


def _daily_loop(librarian: Any) -> None:
    while True:
        try:
            if _due(librarian):
                refresh(librarian)
        except Exception as exc:
            # Bounded diagnostics: the error type only, never provider details.
            logger.error("Lens list refresh failed (%s)", type(exc).__name__)
        time.sleep(DAILY_CHECK_SECONDS)


def start_refresh(librarian: Any) -> threading.Thread:
    """Run one lens refresh in the background, for a manual trigger from the app layer.

    Returns at once. The refresh takes the same lock as the daily loop, so the two never overlap;
    while the setting is off it returns "disabled" without touching the library or the store.
    """
    thread = threading.Thread(
        target=refresh, args=(librarian,), name="navidrome-lens-lists-manual", daemon=True,
    )
    thread.start()
    return thread


def start_daily_refresh(librarian: Any) -> threading.Thread:
    """Start the background loop that rebuilds the lens lists once per local day."""
    thread = threading.Thread(
        target=_daily_loop, args=(librarian,), name="navidrome-lens-lists", daemon=True,
    )
    thread.start()
    return thread
