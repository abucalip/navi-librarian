"""The week of Current tastes lists behind the dashboard's Today's picks.

Pure: no I/O, no clock, no provider call. The store keeps only the latest ``lens:current_tastes``
list, so each day's list is also kept under ``lens_week:current_tastes:<day>``; the picks pool is
the lists of the last seven list days (today included), without owned or dismissed albums and
without repeats. Every request shuffles the pool again, so each dashboard visit shows a new order.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import date, timedelta
from typing import Any

LENS = "current_tastes"
WEEK_DAYS = 7
ARCHIVE_PREFIX = f"lens_week:{LENS}:"
CATEGORY = "Current tastes"


def archive_name(day: str) -> str:
    return f"{ARCHIVE_PREFIX}{day}"


def week_days(today: str, days: int = WEEK_DAYS) -> list[str]:
    """The ISO list days of the window, newest first."""
    end = date.fromisoformat(today)
    return [(end - timedelta(days=offset)).isoformat() for offset in range(days)]


def archive_current(
    stored: Mapping[str, Any] | None,
    read_list: Callable[[str], Mapping[str, Any] | None],
    write_list: Callable[[str, Any], None],
) -> str | None:
    """Keep the stored Current tastes list under its own day. Returns the day written, or None.

    A day already kept is never overwritten, so a later rebuild the same day cannot shrink it.
    """
    payload = stored.get("payload") if isinstance(stored, Mapping) else None
    if not isinstance(payload, Mapping) or not isinstance(payload.get("albums"), list) or not payload["albums"]:
        return None
    day = str(payload.get("day") or "")
    try:
        date.fromisoformat(day)
    except ValueError:
        return None
    if read_list(archive_name(day)):
        return None
    write_list(archive_name(day), dict(payload))
    return day


def _identity(album: Mapping[str, Any], music_key: Callable[[str], str]) -> tuple[str, str]:
    return music_key(str(album.get("artist") or "")), music_key(str(album.get("album") or ""))


def week_pool(
    today: str,
    stored: Mapping[str, Any] | None,
    read_list: Callable[[str], Mapping[str, Any] | None],
    music_key: Callable[[str], str],
    is_owned: Callable[[Mapping[str, Any]], bool] | None = None,
    is_dismissed: Callable[[Mapping[str, Any]], bool] | None = None,
) -> list[dict[str, Any]]:
    """The deduplicated albums of the week's Current tastes lists, newest list first."""
    payloads: list[Any] = []
    for day in week_days(today):
        kept = read_list(archive_name(day))
        if isinstance(kept, Mapping):
            payloads.append(kept.get("payload"))
    if isinstance(stored, Mapping):
        payloads.insert(0, stored.get("payload"))  # the live list: today's, or the latest if a build failed
    pool: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for payload in payloads:
        albums = payload.get("albums") if isinstance(payload, Mapping) else None
        for album in albums if isinstance(albums, list) else []:
            if not isinstance(album, Mapping):
                continue
            identity = _identity(album, music_key)
            if not identity[0] or not identity[1] or identity in seen:
                continue
            seen.add(identity)
            if (is_owned is not None and is_owned(album)) or (is_dismissed is not None and is_dismissed(album)):
                continue
            pool.append(dict(album))
    return pool


def to_pick(album: Mapping[str, Any]) -> dict[str, Any]:
    """A lens album in the dashboard pick shape the clients already read."""
    tag = album.get("seed_tag")
    return {
        "artist": str(album.get("artist") or ""),
        "album": str(album.get("album") or ""),
        "dashboard_category": CATEGORY,
        "genres": [str(t) for t in album.get("tags") or []][:4],
        "reason": f"From your current tastes: {tag}" if tag else "From your current tastes",
        "release_group_mbid": album.get("release_group_mbid"),
        "lastfm_listeners": album.get("album_listeners"),
    }


def build_week_picks(
    pool: list[dict[str, Any]], count: int, shuffle: Callable[[list[Any]], None],
) -> dict[str, Any]:
    """Shuffle a copy of the pool and answer the first ``count`` as picks."""
    order = list(pool)
    shuffle(order)
    items = [to_pick(album) for album in order[:count]]
    return {"items": items, "count": len(items), "pool_size": len(pool)}
