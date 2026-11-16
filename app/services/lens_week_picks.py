"""Today's picks from the week's Current tastes lists (connects discovery.lens_week to the store).

Kept outside ``navidrome_server.py`` (D-016). Reads helpers off the librarian object at call time,
as ``discovery.lens_service`` does.
"""
from __future__ import annotations

import random
from datetime import datetime
from typing import Any

from discovery import lens_week
from discovery.deep_dive_bridge import bridge_albums
from discovery.lens_service import _dismissed_or_none, _owned_or_none
from discovery.lens_storage import lens_day, lens_storage_name


def keep_today(librarian: Any) -> None:
    """Keep the stored Current tastes list under its day. Never raises: a failure only skips the copy."""
    try:
        stored = librarian._discovery_read_list(lens_storage_name(lens_week.LENS))
        lens_week.archive_current(stored, librarian._discovery_read_list, librarian._discovery_write_list)
    except Exception:
        pass


# The pool is reshuffled on every visit, so it may be wider than a list's 2 per family and 10 in all.
BRIDGE_PER_FAMILY = 4
BRIDGE_TOTAL = 30


def picks(librarian: Any, count: int, shuffle=random.shuffle) -> dict[str, Any]:
    keep_today(librarian)
    stored = librarian._discovery_read_list(lens_storage_name(lens_week.LENS))
    is_owned, is_dismissed = _owned_or_none(librarian), _dismissed_or_none(librarian)
    pool = lens_week.week_pool(
        lens_day(datetime.now()), stored, librarian._discovery_read_list, librarian._music_key,
        is_owned, is_dismissed,
    )
    # The Current tastes list now grows with Deep Dives albums of the same genres (read time); the
    # picks draw from that grown list too, or the same few albums come back every visit.
    try:
        payload = stored.get("payload") if isinstance(stored, dict) else None
        deep = librarian._discovery_read_list("artist_deep_dive")
        pool += bridge_albums(
            lens_week.LENS, pool, (payload or {}).get("seed_tags") or [],
            deep.get("payload") if isinstance(deep, dict) else None, librarian._music_key,
            is_excluded=lambda item: bool((is_owned and is_owned(item)) or (is_dismissed and is_dismissed(item))),
            per_family=BRIDGE_PER_FAMILY, total=BRIDGE_TOTAL,
        )
    except Exception:
        pass  # a failed bridge only leaves the week's own albums
    return lens_week.build_week_picks(pool, count, shuffle)
