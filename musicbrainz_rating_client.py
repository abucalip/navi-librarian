"""Cached MusicBrainz release-group rating lookup."""
from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

import httpx


def critical_rating(
    mbid: str | None,
    include_year: bool = False,
    *,
    cache_get: Callable[[str, int], Any],
    cache_set: Callable[[str, Any], None],
    http_get: Callable[..., Any] | None = None,
    sleep: Callable[[float], None] | None = None,
) -> dict[str, Any] | None:
    """Fetch rating/vote/year metadata with the established cache and pacing rules."""
    if not mbid:
        return None
    cache_key = "discovery:mb-release-group-rating:" + str(mbid)
    cached = cache_get(cache_key, ttl_seconds=180 * 24 * 60 * 60)
    if cached is not None and (not include_year or "year" in cached):
        return cached
    request = http_get or httpx.get
    pause = sleep or time.sleep
    try:
        # MusicBrainz requests must be spaced to respect its public API limit.
        pause(1.1)
        response = request(
            f"https://musicbrainz.org/ws/2/release-group/{mbid}",
            params={"fmt": "json", "inc": "ratings"},
            headers={"User-Agent": "NavidromeLibrarian/1.0 (personal music discovery)"},
            timeout=15,
        )
        if response.status_code == 404:
            empty_result = {"rating": None, "votes": 0, "year": None}
            cache_set(cache_key, empty_result)
            return empty_result
        response.raise_for_status()
        data = response.json()
        rating = data.get("rating") or {}
        release_date = str(data.get("first-release-date") or "")
        year_text = release_date[:4]
        result = {
            "rating": rating.get("value"),
            "votes": int(rating.get("votes-count") or 0),
            "year": int(year_text) if year_text.isdigit() and 1900 <= int(year_text) <= 2100 else None,
        }
        cache_set(cache_key, result)
        return result
    except (httpx.HTTPError, ValueError, TypeError):
        return None
