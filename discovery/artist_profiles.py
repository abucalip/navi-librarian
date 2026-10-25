"""Artist area and first-year profiles for the regional spine and era match (Engine 2, Current tastes).

One batched MusicBrainz artist search (``arid:(...)``) per chunk of artists returns each artist's
area name and life-span begin year. Answers are cached per artist for 90 days, a not-found artist
is cached too, and a failed chunk leaves its artists uncached so the next run asks again. Never
raises. Injected HTTP and cache callables keep tests offline. See docs/engine2.md.
"""
from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from typing import Any

from discovery.mbid_popularity import MUSICBRAINZ_SPACING_SECONDS

MUSICBRAINZ_ARTIST_SEARCH_URL = "https://musicbrainz.org/ws/2/artist/"
ARTIST_PROFILE_CACHE_PREFIX = "mb:artist-profile:"
ARTIST_PROFILE_TTL_SECONDS = 90 * 24 * 60 * 60
# Artists per search; the page size below must cover one chunk.
ARTIST_PROFILE_CHUNK = 20
ARTIST_PROFILE_PAGE = 25
# Searches per run. At 20 artists a search, 240 artists fit; more are left for a later run.
ARTIST_PROFILE_MAX_CALLS = 12


def _chunks(values: list[str], size: int):
    for start in range(0, len(values), size):
        yield values[start:start + size]


def _begin_year(entry: Mapping[str, Any]) -> int | None:
    life = entry.get("life-span")
    begin = str(life.get("begin") or "") if isinstance(life, Mapping) else ""
    year = begin[:4]
    return int(year) if year.isdigit() else None


def _area_name(entry: Mapping[str, Any]) -> str | None:
    area = entry.get("area")
    name = str(area.get("name") or "").strip() if isinstance(area, Mapping) else ""
    return name or None


def fetch_artist_profiles(
    get: Callable[..., Any],
    artist_mbids: Iterable[str],
    *,
    headers: Mapping[str, str],
    cache_get: Callable[..., Any],
    cache_set: Callable[..., Any],
    sleep: Callable[[float], Any] | None = None,
    timeout: float = 30,
) -> dict[str, dict[str, Any]]:
    """Return {artist MBID: {"area": name or None, "begin_year": int or None}} for the artists asked.

    Cached artists cost nothing. At most ``ARTIST_PROFILE_MAX_CALLS`` searches run; artists beyond
    that, and artists in a failed search, are missing from the result. Never raises."""
    from recommendation_run_metrics import record_provider_call

    found: dict[str, dict[str, Any]] = {}
    uncached: list[str] = []
    for mbid in dict.fromkeys(str(m) for m in artist_mbids if m):
        try:
            cached = cache_get(f"{ARTIST_PROFILE_CACHE_PREFIX}{mbid}", ttl_seconds=ARTIST_PROFILE_TTL_SECONDS)
        except Exception:
            cached = None
        if isinstance(cached, Mapping) and "area" in cached and "begin_year" in cached:
            found[mbid] = {"area": cached["area"], "begin_year": cached["begin_year"]}
        else:
            uncached.append(mbid)

    calls = 0
    for chunk in _chunks(uncached, ARTIST_PROFILE_CHUNK):
        if calls >= ARTIST_PROFILE_MAX_CALLS:
            break
        calls += 1
        try:
            record_provider_call("musicbrainz", "artist_search_batch")
            response = get(
                MUSICBRAINZ_ARTIST_SEARCH_URL,
                params={"query": "arid:(" + " OR ".join(chunk) + ")", "limit": ARTIST_PROFILE_PAGE, "fmt": "json"},
                headers=dict(headers),
                timeout=timeout,
            )
            if sleep is not None:
                sleep(MUSICBRAINZ_SPACING_SECONDS)
            if response.status_code != 200:
                continue
            body = response.json()
            artists = body.get("artists") if isinstance(body, dict) else None
            if not isinstance(artists, list):
                continue
        except Exception:
            continue
        by_id = {str(entry.get("id")): entry for entry in artists if isinstance(entry, Mapping)}
        for mbid in chunk:
            entry = by_id.get(mbid)
            profile = {"area": _area_name(entry), "begin_year": _begin_year(entry)} if entry else {
                "area": None, "begin_year": None}
            found[mbid] = profile
            try:
                cache_set(f"{ARTIST_PROFILE_CACHE_PREFIX}{mbid}", profile)
            except Exception:
                pass
    return found
