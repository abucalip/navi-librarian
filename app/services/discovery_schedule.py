"""Scheduled discovery list refreshes, run by the worker (efficiency W3).

Before W3 the web process started two loops: the legacy discovery scheduler (``navidrome_server``) and the
daily lens-list refresh (``discovery/lens_service.py``). Each slept an hour between checks. They are now two
entries of a worker scheduler (``app/worker_schedule.py``), each checked hourly (``interval``), and each
``run`` is one pass of the old loop body: the same functions, arguments, due rules and log lines.

- ``discovery_lists``: refresh every list older than 24 hours (``refresh_stale_lists``), and none while
  automatic refill is off. Each list goes through ``librarian._discovery_scheduler_refresh_one``, so the
  personal list keeps ``origin="scheduler"``.
- ``lens_lists``: when ``lens_service._due`` (the setting is on and a lens list is not from today), run
  ``lens_service.refresh_exclusive``.

Each list refresh, here and in the web, goes through ``discovery/refresh_guard.py``, so the worker and a
manual or read-triggered refresh in the web never refresh the same list at once. The entries run on their
own scheduler thread (``worker-schedule-discovery``), so the long similar-artist precompute on the main
schedule thread does not hold them back.

The librarian's helpers are read by attribute at call time; this module does not import the legacy server.
"""
from __future__ import annotations

import logging
import time

from app import worker_schedule
from app.api.insights import STORE_FILE
from app.services import playlist_inbox_refresh
from app.services.playlist_reconcile import PlaylistReconciler
from discovery import lens_service
from discovery import refresh as discovery_refresh
from integrations.navidrome.playlists import PlaylistClient
from settings import service as settings_service

logger = logging.getLogger(__name__)

CHECK_SECONDS = 3600     # the old scheduler loop slept this long between passes
PLAYLIST_SCAN_SECONDS = 300
LIST_NAMES = ("personal", "classics", "artist_deep_dive", "new_releases", "listening_profile")
THREAD_NAME = "worker-schedule-discovery"


def refresh_stale_lists_once(librarian):
    """One pass of the old hourly discovery scheduler; per-list failures are logged by error type only."""
    try:
        enabled = settings_service.automatic_refill_enabled_value(librarian._discovery_settings_read)
        outcomes = discovery_refresh.refresh_stale_lists(
            LIST_NAMES if enabled else (),
            librarian._discovery_read_list,
            librarian._discovery_scheduler_refresh_one,
            now=time.time(),
            max_age_seconds=discovery_refresh.STALE_MAX_AGE_SECONDS,
        )
    except Exception as exc:
        logger.error("Discovery scheduler cycle failed (%s)", type(exc).__name__)
        return None
    for outcome in outcomes:
        if outcome["status"] in {"read_failed", "refresh_failed"}:
            logger.warning(
                "Discovery scheduler %s failed for %s (%s)",
                outcome.get("stage", "refresh"), outcome["list"], outcome.get("error_type", "reported_error"),
            )
    return outcomes


def refresh_lens_lists_once(librarian):
    """One pass of the old daily lens loop: refresh when a lens list is missing or not from today."""
    try:
        if lens_service._due(librarian):
            return lens_service.refresh_exclusive(librarian)
    except Exception as exc:
        # Bounded diagnostics: the error type only, never provider details.
        logger.error("Lens list refresh failed (%s)", type(exc).__name__)
    return None


def reconcile_playlists_once(librarian, reconciler):
    try:
        navidrome = PlaylistClient(librarian._navidrome_config())
    except ValueError:
        return None
    return reconciler.run_once(navidrome)


def entries(librarian):
    """The discovery scheduler's entries in execution order when due."""
    path = librarian.DATA_DIR / STORE_FILE
    reconciler = PlaylistReconciler(path, max_idle_seconds=CHECK_SECONDS)
    return (
        worker_schedule.Entry("discovery_lists", worker_schedule.interval(CHECK_SECONDS),
                              lambda: refresh_stale_lists_once(librarian)),
        worker_schedule.Entry("lens_lists", worker_schedule.interval(lens_service.DAILY_CHECK_SECONDS),
                              lambda: refresh_lens_lists_once(librarian)),
        worker_schedule.Entry("playlist_inbox_refresh", worker_schedule.interval(CHECK_SECONDS),
                              lambda: playlist_inbox_refresh.refresh_once(librarian, path)),
        worker_schedule.Entry("playlist_reconcile", worker_schedule.interval(PLAYLIST_SCAN_SECONDS),
                              lambda: reconcile_playlists_once(librarian, reconciler),
                              retry_seconds=worker_schedule.TICK_SECONDS),
    )
