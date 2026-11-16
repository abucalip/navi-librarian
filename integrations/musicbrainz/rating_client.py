"""Cached MusicBrainz release-group rating lookup."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx

from integrations.provider_gate import musicbrainz_lane

RATING_MAX_WAIT = 60.0  # a Classics build queues for a slot; it does not give up early


def critical_rating(
    mbid: str | None,
    include_year: bool = False,
    *,
    cache_get: Callable[[str, int], Any],
    cache_set: Callable[[str, Any], None],
    http_get: Callable[..., Any] | None = None,
    lane: Any = None,
) -> dict[str, Any] | None:
    """Fetch rating/vote/year metadata with the established cache and pacing rules."""
    if not mbid:
        return None
    cache_key = "discovery:mb-release-group-rating:" + str(mbid)
    cached = cache_get(cache_key, ttl_seconds=180 * 24 * 60 * 60)
    if cached is not None and (not include_year or "year" in cached):
        return cached
    request = http_get or httpx.get
    try:
        # MusicBrainz requests take a slot from the shared gate to respect its public API limit.
        lane = lane or musicbrainz_lane(RATING_MAX_WAIT)
        if not lane.acquire():
            return None
        from recommendation_run_metrics import record_provider_call
        record_provider_call("musicbrainz", "release_group_rating")
        response = request(
            f"https://musicbrainz.org/ws/2/release-group/{mbid}",
            params={"fmt": "json", "inc": "ratings"},
            headers={"User-Agent": "Discair/1.0 (personal music discovery)"},
            timeout=15,
        )
        lane.penalize_response(response)
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
