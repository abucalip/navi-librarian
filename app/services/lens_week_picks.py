"""Today's picks from the week's Current tastes lists (connects discovery.lens_week to the store).

Kept outside ``navidrome_server.py`` (D-016). Reads helpers off the librarian object at call time,
as ``discovery.lens_service`` does.
"""
from __future__ import annotations

import random
from datetime import datetime
from typing import Any

from discovery import lens_week
from discovery.lens_service import _dismissed_or_none, _owned_or_none
from discovery.lens_storage import lens_day, lens_storage_name


def keep_today(librarian: Any) -> None:
    """Keep the stored Current tastes list under its day. Never raises: a failure only skips the copy."""
    try:
        stored = librarian._discovery_read_list(lens_storage_name(lens_week.LENS))
        lens_week.archive_current(stored, librarian._discovery_read_list, librarian._discovery_write_list)
    except Exception:
        pass


def picks(librarian: Any, count: int, shuffle=random.shuffle) -> dict[str, Any]:
    keep_today(librarian)
    stored = librarian._discovery_read_list(lens_storage_name(lens_week.LENS))
    pool = lens_week.week_pool(
        lens_day(datetime.now()), stored, librarian._discovery_read_list, librarian._music_key,
        _owned_or_none(librarian), _dismissed_or_none(librarian),
    )
    return lens_week.build_week_picks(pool, count, shuffle)
