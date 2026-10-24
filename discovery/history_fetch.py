"""Dynamic listening-history fetch for the daily lens lists (Engine 2, Phase 4).

ListenBrainz and Last.fm hold the same listens, so the history is split between them rather
than read from both: the walk goes back one window at a time, and window ``i`` is read from
source ``i mod n``. If that source fails for a window, the next source answers it. The walk
stops once enough usable listens are in hand, or when the floor of ``max_days`` is reached.
Listens seen in more than one window or source are counted once.

Pure apart from the injected window readers: no provider is called here directly, and nothing
is logged except aggregate counts. See docs/engine2.md (Phase 4).
"""
from __future__ import annotations

import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from discovery.lens_lists import usable_listens

DAY_SECONDS = 86400
LENS_HISTORY_STEP_DAYS = 365
# Starting value, not a measured threshold. At 500 the walk stopped inside the most recent year
# (571 listens), which left Repeated tracks with no seeds; 2000 reaches back to 2014 on the
# measured history. The owner confirms or changes it.
LENS_MIN_USABLE_LISTENS = 2000
# Floor of the walk: 13 years back, which reaches 2013 from 2026 (the test history has 2014 data).
LENS_HISTORY_MAX_DAYS = 13 * 365
LISTENBRAINZ_PAGE = 100
LASTFM_PAGE = 200
MAX_PAGES_PER_WINDOW = 50
# A window that returns this many listens may have been cut by MAX_PAGES_PER_WINDOW (50 pages of
# 100 ListenBrainz listens). It is flagged so the cut is visible in the diagnostics.
WINDOW_LISTEN_CAP = LISTENBRAINZ_PAGE * MAX_PAGES_PER_WINDOW
PAUSE_SECONDS = 0.25

WindowReader = Callable[[int, int], list[dict[str, Any]]]


class LastFmResponseError(RuntimeError):
    """A Last.fm reply that is an API error or does not have the expected shape.

    Last.fm sends errors (an unknown user, a bad key) with HTTP 200, so the status code alone
    does not show a failed read. Raising lets the walk answer the window from the other source.
    """


def _key(listen: Mapping[str, Any]) -> tuple:
    metadata = listen.get("track_metadata") if isinstance(listen.get("track_metadata"), Mapping) else {}
    return (
        int(float(listen.get("listened_at") or 0)),
        str(metadata.get("artist_name") or "").strip().lower(),
        str(metadata.get("track_name") or "").strip().lower(),
    )


def listenbrainz_window(
    username: str,
    start: int,
    end: int,
    *,
    get: Callable[..., Any],
    headers: Mapping[str, str],
    pause: Callable[[float], None] = time.sleep,
) -> list[dict[str, Any]]:
    """Read ListenBrainz listens stamped in ``(start, end]``, newest first.

    Pages backwards with ``max_ts`` only. Passing ``min_ts`` makes the API return the oldest
    page after the bound, which is why the window is bounded here by checking each listen.
    """
    listens: list[dict[str, Any]] = []
    max_ts = end
    for _ in range(MAX_PAGES_PER_WINDOW):
        response = get(
            f"https://api.listenbrainz.org/1/user/{username}/listens",
            params={"count": LISTENBRAINZ_PAGE, "max_ts": max_ts},
            headers=dict(headers),
            timeout=30,
        )
        response.raise_for_status()
        page = response.json().get("payload", {}).get("listens", [])
        if not page:
            break
        in_window = [item for item in page if start < int(item.get("listened_at", 0)) <= end]
        listens.extend(in_window)
        oldest = min(int(item.get("listened_at", 0)) for item in page)
        if len(page) < LISTENBRAINZ_PAGE or oldest <= start:
            break
        max_ts = oldest - 1
        pause(PAUSE_SECONDS)
    return listens


def lastfm_window(
    username: str,
    api_key: str,
    start: int,
    end: int,
    *,
    get: Callable[..., Any],
    pause: Callable[[float], None] = time.sleep,
) -> list[dict[str, Any]]:
    """Read Last.fm scrobbles in ``(start, end]`` and convert them to the ListenBrainz shape.

    ``user.getRecentTracks`` is bounded by ``from`` and ``to`` and returns newest first. The
    now-playing entry has no date and is skipped.
    """
    listens: list[dict[str, Any]] = []
    total_pages = 1
    page_number = 1
    while page_number <= min(total_pages, MAX_PAGES_PER_WINDOW):
        response = get(
            "https://ws.audioscrobbler.com/2.0/",
            params={
                "method": "user.getrecenttracks", "user": username, "api_key": api_key,
                "format": "json", "limit": LASTFM_PAGE, "page": page_number,
                "from": start + 1, "to": end,
            },
            timeout=30,
        )
        response.raise_for_status()
        body = response.json()
        if not isinstance(body, dict) or "error" in body:
            raise LastFmResponseError("Last.fm returned an API error")
        recent = body.get("recenttracks")
        if not isinstance(recent, dict):
            raise LastFmResponseError("Last.fm response has no recenttracks object")
        tracks = recent.get("track", [])
        # Last.fm sends a single track as an object rather than a one-item list.
        if isinstance(tracks, dict):
            tracks = [tracks]
        if not isinstance(tracks, list):
            raise LastFmResponseError("Last.fm track list has an unexpected shape")
        total_pages = int(recent.get("@attr", {}).get("totalPages", 1) or 1)
        for item in tracks:
            stamp = (item.get("date") or {}).get("uts")
            if stamp is None:
                continue
            artist = item.get("artist") or {}
            album = item.get("album") or {}
            artist_mbid = artist.get("mbid") or ""
            listens.append({
                "listened_at": int(stamp),
                "track_metadata": {
                    "artist_name": artist.get("#text") or artist.get("name") or "",
                    "track_name": item.get("name") or "",
                    "release_name": album.get("#text") or "",
                    "additional_info": {"artist_mbids": [artist_mbid] if artist_mbid else []},
                },
            })
        page_number += 1
        pause(PAUSE_SECONDS)
    return listens


def fetch_lens_history(
    sources: Sequence[tuple[str, WindowReader]],
    *,
    now: float,
    min_usable: int = LENS_MIN_USABLE_LISTENS,
    step_days: int = LENS_HISTORY_STEP_DAYS,
    max_days: int = LENS_HISTORY_MAX_DAYS,
) -> dict[str, Any]:
    """Walk back from ``now`` one window at a time until enough usable listens are collected.

    Window ``i`` is tried on source ``i mod n`` first, then on the others in order. Returns the
    merged listens and aggregate diagnostics: one entry per window with its source and count,
    and how many windows no source could answer.
    """
    if not sources:
        return {"listens": [], "windows": [], "unanswered": 0, "stopped": "no_sources"}
    end = int(now)
    floor = end - max_days * DAY_SECONDS
    step = step_days * DAY_SECONDS
    seen: set[tuple] = set()
    listens: list[dict[str, Any]] = []
    windows: list[dict[str, Any]] = []
    unanswered = 0
    index = 0
    stopped = "floor_reached"
    while end > floor:
        start = max(end - step, floor)
        order = [(index + offset) % len(sources) for offset in range(len(sources))]
        answered = None
        for position in order:
            name, read = sources[position]
            try:
                answered = (name, read(start, end))
                break
            except Exception:
                continue
        if answered is None:
            unanswered += 1
            windows.append({"source": None, "count": 0})
        else:
            name, found = answered
            added = 0
            for listen in found:
                key = _key(listen)
                if key not in seen:
                    seen.add(key)
                    listens.append(listen)
                    added += 1
            windows.append({"source": name, "count": added, "truncated": len(found) >= WINDOW_LISTEN_CAP})
        index += 1
        end = start
        if len(usable_listens(listens)) >= min_usable:
            stopped = "enough_listens"
            break
    return {"listens": listens, "windows": windows, "unanswered": unanswered, "stopped": stopped}
