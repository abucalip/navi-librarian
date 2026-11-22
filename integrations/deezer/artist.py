"""Paced, cached Deezer artist fallback client (FirstFM F2.1).

Used only as a fallback when ListenBrainz has no data or an artist has no MBID.
Deezer's public REST API has no multi-artist batch endpoint for ``/artist/{id}/related``
or ``/artist/{id}/top`` and allows ~50 requests per 5 seconds per IP, so all calls share
a 0.15 s spacing guard, 30-day positive caching, and 1-hour no-match negative marks.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Callable
from urllib.parse import urlencode

DEEZER_API_BASE = "https://api.deezer.com"
DEEZER_SPACING_SECONDS = 0.15
POSITIVE_TTL_SECONDS = 30 * 24 * 60 * 60
NEGATIVE_TTL_SECONDS = 60 * 60
DEFAULT_FETCH_LIMIT = 50
SEARCH_LIMIT = 8

ARTIST_SEARCH_CACHE_PREFIX = "deezer:artist:search:"
ARTIST_NO_MATCH_PREFIX = "deezer:artist:no-match:"
RELATED_ARTISTS_CACHE_PREFIX = "deezer:artist:related:"
RELATED_ARTISTS_NO_MATCH_PREFIX = "deezer:artist:related:no-match:"
TOP_TRACKS_CACHE_PREFIX = "deezer:artist:top:"
TOP_TRACKS_NO_MATCH_PREFIX = "deezer:artist:top:no-match:"


class DeezerPacer:
    """Thread-safe spacing guard keeping Deezer requests at least ``spacing`` seconds apart."""

    def __init__(
        self,
        spacing: float = DEEZER_SPACING_SECONDS,
        *,
        monotonic: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._spacing = max(0.0, float(spacing))
        self._monotonic = monotonic
        self._sleep = sleep
        self._lock = threading.Lock()
        self._next_at = 0.0

    def wait(self) -> None:
        """Reserve the next request slot and sleep outside the lock if needed."""
        if self._spacing <= 0:
            return
        with self._lock:
            now = self._monotonic()
            slot = max(now, self._next_at)
            delay = slot - now
            self._next_at = slot + self._spacing
        if delay > 0:
            self._sleep(delay)


_DEFAULT_PACER = DeezerPacer()


def _clean_name(name: str) -> str:
    return " ".join(str(name or "").split())


def _safe_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _read_cache(cache_get: Callable[..., Any], key: str, ttl_seconds: int) -> Any:
    try:
        return cache_get(key, ttl_seconds=ttl_seconds)
    except Exception:
        return None


def _write_cache(cache_set: Callable[[str, Any], None], key: str, value: Any) -> None:
    try:
        cache_set(key, value)
    except Exception:
        pass


def _is_fresh_negative(cache_get: Callable[..., Any], key: str, now: float) -> bool:
    stored = _read_cache(cache_get, key, NEGATIVE_TTL_SECONDS)
    if not isinstance(stored, dict) or not stored.get("negative"):
        return False
    at = stored.get("at")
    return isinstance(at, (int, float)) and not isinstance(at, bool) and 0 <= now - at < NEGATIVE_TTL_SECONDS


def _write_negative(cache_set: Callable[[str, Any], None], key: str, now: float) -> None:
    _write_cache(cache_set, key, {"negative": True, "at": now})


def _get_data_list(
    get: Callable[..., Any],
    pacer: DeezerPacer | None,
    url: str,
    timeout: float,
) -> list[Any] | None:
    """Perform one paced GET and return ``body["data"]``, or None on HTTP/API failure."""
    (pacer or _DEFAULT_PACER).wait()
    try:
        response = get(url, timeout=timeout)
        if getattr(response, "status_code", None) != 200:
            return None
        body = response.json()
    except Exception:
        return None
    if not isinstance(body, dict) or body.get("error"):
        return None
    data = body.get("data")
    return data if isinstance(data, list) else None


def _pick_exact_artist(items: list[Any], target_name: str) -> dict[str, Any] | None:
    target_key = target_name.casefold()
    exact: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if _safe_int(item.get("id")) is None:
            continue
        if _clean_name(str(item.get("name") or "")).casefold() == target_key:
            exact.append(item)
    if not exact:
        return None
    return max(exact, key=lambda item: max(0, _safe_int(item.get("nb_fan")) or 0))


def search_artist_id(
    get: Callable[..., Any],
    cache_get: Callable[..., Any],
    cache_set: Callable[[str, Any], None],
    name: str,
    *,
    timeout: float = 10.0,
    clock: Callable[[], float] = time.time,
    pacer: DeezerPacer | None = None,
) -> int | None:
    """Resolve an exact-name Deezer artist ID, cached 30 days with 1-hour no-match marks."""
    cleaned = _clean_name(name)
    if not cleaned:
        return None
    norm = cleaned.casefold()
    pos_key = f"{ARTIST_SEARCH_CACHE_PREFIX}{norm}"
    neg_key = f"{ARTIST_NO_MATCH_PREFIX}{norm}"

    cached = _read_cache(cache_get, pos_key, POSITIVE_TTL_SECONDS)
    if isinstance(cached, dict):
        cached_id = _safe_int(cached.get("id"))
        if cached_id is not None:
            return cached_id
    elif isinstance(cached, int) and not isinstance(cached, bool):
        return cached

    if _is_fresh_negative(cache_get, neg_key, clock()):
        return None

    query = urlencode({"q": cleaned, "limit": SEARCH_LIMIT})
    items = _get_data_list(get, pacer, f"{DEEZER_API_BASE}/search/artist?{query}", timeout)
    if items is None:
        return None

    match = _pick_exact_artist(items, cleaned)
    if match is None:
        _write_negative(cache_set, neg_key, clock())
        return None

    artist_id = _safe_int(match.get("id"))
    if artist_id is None:
        return None
    _write_cache(cache_set, pos_key, {"id": artist_id, "name": str(match.get("name") or cleaned)})
    return artist_id


def related_artists(
    get: Callable[..., Any],
    cache_get: Callable[..., Any],
    cache_set: Callable[[str, Any], None],
    artist_id: int | str,
    limit: int = 20,
    *,
    timeout: float = 10.0,
    clock: Callable[[], float] = time.time,
    pacer: DeezerPacer | None = None,
) -> list[dict[str, Any]]:
    """Fetch related artists for a Deezer ``artist_id``, cached 30 days with 1-hour empty marks."""
    aid = _safe_int(artist_id)
    if aid is None or aid <= 0 or limit <= 0:
        return []

    pos_key = f"{RELATED_ARTISTS_CACHE_PREFIX}{aid}"
    neg_key = f"{RELATED_ARTISTS_NO_MATCH_PREFIX}{aid}"

    cached = _read_cache(cache_get, pos_key, POSITIVE_TTL_SECONDS)
    if isinstance(cached, list) and len(cached) >= min(limit, DEFAULT_FETCH_LIMIT):
        return cached[:limit]
    if isinstance(cached, list) and limit <= DEFAULT_FETCH_LIMIT:
        return cached[:limit]

    if _is_fresh_negative(cache_get, neg_key, clock()):
        return []

    fetch_limit = max(int(limit), DEFAULT_FETCH_LIMIT)
    query = urlencode({"limit": fetch_limit})
    items = _get_data_list(get, pacer, f"{DEEZER_API_BASE}/artist/{aid}/related?{query}", timeout)
    if items is None:
        return []

    parsed: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        rel_name = _clean_name(str(item.get("name") or ""))
        rel_id = _safe_int(item.get("id"))
        if not rel_name or rel_id is None:
            continue
        parsed.append({
            "id": rel_id,
            "name": rel_name,
            "nb_fan": max(0, _safe_int(item.get("nb_fan")) or 0),
        })

    if not parsed:
        _write_negative(cache_set, neg_key, clock())
        return []

    _write_cache(cache_set, pos_key, parsed)
    return parsed[:limit]


def top_tracks(
    get: Callable[..., Any],
    cache_get: Callable[..., Any],
    cache_set: Callable[[str, Any], None],
    artist_id: int | str,
    limit: int = 10,
    *,
    timeout: float = 10.0,
    clock: Callable[[], float] = time.time,
    pacer: DeezerPacer | None = None,
) -> list[dict[str, Any]]:
    """Fetch top tracks for a Deezer ``artist_id``, cached 30 days with 1-hour empty marks."""
    aid = _safe_int(artist_id)
    if aid is None or aid <= 0 or limit <= 0:
        return []

    pos_key = f"{TOP_TRACKS_CACHE_PREFIX}{aid}"
    neg_key = f"{TOP_TRACKS_NO_MATCH_PREFIX}{aid}"

    cached = _read_cache(cache_get, pos_key, POSITIVE_TTL_SECONDS)
    if isinstance(cached, list) and (len(cached) >= limit or limit <= DEFAULT_FETCH_LIMIT):
        return cached[:limit]

    if _is_fresh_negative(cache_get, neg_key, clock()):
        return []

    fetch_limit = max(int(limit), DEFAULT_FETCH_LIMIT)
    query = urlencode({"limit": fetch_limit})
    items = _get_data_list(get, pacer, f"{DEEZER_API_BASE}/artist/{aid}/top?{query}", timeout)
    if items is None:
        return []

    parsed: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        title = _clean_name(str(item.get("title") or item.get("title_short") or ""))
        if not title:
            continue
        album_obj = item.get("album")
        album_title = _clean_name(str(album_obj.get("title") or "")) if isinstance(album_obj, dict) else ""
        parsed.append({
            "id": _safe_int(item.get("id")),
            "name": title,
            "rank": _safe_int(item.get("rank")),
            "duration": _safe_int(item.get("duration")),
            "album": album_title or None,
        })

    if not parsed:
        _write_negative(cache_set, neg_key, clock())
        return []

    _write_cache(cache_set, pos_key, parsed)
    return parsed[:limit]
