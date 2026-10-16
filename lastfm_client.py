"""Rate-limited, cached Last.fm HTTP client used by discovery services."""
from __future__ import annotations

import hashlib
import json
import threading
import time
from collections.abc import Callable, Mapping
from typing import Any

import httpx

from discovery_recommendations import music_key


def _default_items(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


class LastFmClient:
    """Last.fm transport with injected settings/cache dependencies."""

    def __init__(
        self,
        *,
        settings_reader: Callable[[], Mapping[str, Any]],
        cache_get: Callable[[str, int], Any],
        cache_set: Callable[[str, Any], None],
        http_get: Callable[..., Any] | None = None,
        monotonic: Callable[[], float] | None = None,
        sleep: Callable[[float], None] | None = None,
        request_lock: Any | None = None,
        key_normalizer: Callable[[Any], str] | None = None,
        items_normalizer: Callable[[Any], list[Any]] | None = None,
    ):
        self._settings_reader = settings_reader
        self._cache_get = cache_get
        self._cache_set = cache_set
        self._http_get = http_get or httpx.get
        self._monotonic = monotonic or time.monotonic
        self._sleep = sleep or time.sleep
        self._request_lock = request_lock or threading.Lock()
        self._last_request_at = 0.0
        self._key_normalizer = key_normalizer or music_key
        self._items_normalizer = items_normalizer or _default_items

    def cached_call(self, method: str, ttl_seconds: int = 30 * 24 * 60 * 60, **params: Any) -> Any:
        """Return cached provider data or fetch it with the existing pacing policy."""
        api_key = str(self._settings_reader().get("lastfm_api_key") or "").strip()
        if not api_key:
            return None
        cache_identity = json.dumps(
            {"method": method, "params": params},
            sort_keys=True,
            ensure_ascii=False,
        )
        cache_key = "discovery:lastfm:" + hashlib.sha256(
            cache_identity.encode("utf-8")
        ).hexdigest()
        cached = self._cache_get(cache_key, ttl_seconds)
        if cached is not None:
            return cached
        try:
            with self._request_lock:
                wait = 0.2 - (self._monotonic() - self._last_request_at)
                if wait > 0:
                    self._sleep(wait)
                self._last_request_at = self._monotonic()
            response = self._http_get(
                "https://ws.audioscrobbler.com/2.0/",
                params={
                    "method": method,
                    "api_key": api_key,
                    "format": "json",
                    "autocorrect": 1,
                    **params,
                },
                headers={"User-Agent": "NavidromeLibrarian/1.0"},
                timeout=15,
            )
            response.raise_for_status()
            payload = response.json()
            if payload.get("error"):
                return None
            self._cache_set(cache_key, payload)
            return payload
        except (httpx.HTTPError, ValueError, TypeError, AttributeError):
            return None


    def artist_genres(self, artist: str) -> list[str]:
        """Return up to eight distinct cached Last.fm top tags for an artist."""
        payload = self.cached_call(
            "artist.getTopTags",
            ttl_seconds=30 * 24 * 60 * 60,
            artist=artist,
        )
        if not payload:
            return []
        records = self._items_normalizer((payload.get("toptags") or {}).get("tag"))
        tags = []
        seen = set()
        for record in records:
            if not isinstance(record, dict):
                continue
            name = str(record.get("name") or "").strip()
            key = name.casefold()
            if name and key not in seen:
                tags.append(name)
                seen.add(key)
            if len(tags) >= 8:
                break
        return tags


    def album_popularity(
        self, artist: str, album: str
    ) -> tuple[dict[str, Any] | None, str | None]:
        """Return cached Last.fm album statistics and an optional diagnostic.

        This preserves the older album.getInfo cache identity and error mapping
        used by the recommendation endpoint. A 404 is an ordinary miss for
        niche releases and therefore returns no diagnostic.
        """
        api_key = str(self._settings_reader().get("lastfm_api_key") or "").strip()
        if not api_key or not artist or not album:
            return None, None

        cache_key = (
            "lastfm:album-info-v2:"
            + self._key_normalizer(artist)
            + ":"
            + self._key_normalizer(album)
        )
        cached = self._cache_get(cache_key, 30 * 24 * 60 * 60)
        if cached is not None:
            return cached, None

        try:
            response = self._http_get(
                "https://ws.audioscrobbler.com/2.0/",
                params={
                    "method": "album.getInfo",
                    "api_key": api_key,
                    "artist": artist,
                    "album": album,
                    "autocorrect": 1,
                    "format": "json",
                },
                headers={"User-Agent": "NavidromeLibrarian/1.0"},
                timeout=12,
            )
            response.raise_for_status()
            payload = response.json()
            if payload.get("error"):
                return None, (
                    f"Last.fm API error {payload.get('error')}: "
                    f"{payload.get('message', 'Unknown API error')}"
                )
            data = payload.get("album", {})
            # album.getInfo exposes listeners/playcount directly on the album
            # object; accept a nested stats object too for response compatibility.
            stats = data.get("stats") or data
            if not data or not (
                stats.get("listeners") is not None
                or stats.get("playcount") is not None
            ):
                return None, "Last.fm returned no album statistics for a lookup."
            raw_tags = self._items_normalizer((data.get("tags") or {}).get("tag"))
            result = {
                "listeners": int(stats.get("listeners") or 0),
                "playcount": int(stats.get("playcount") or 0),
                "tags": [
                    item.get("name", "").strip().casefold()
                    for item in raw_tags
                    if isinstance(item, dict) and item.get("name", "").strip()
                ],
            }
            self._cache_set(cache_key, result)
            return result, None
        except httpx.HTTPStatusError as exc:
            # Album-not-found is normal for niche/poorly indexed releases.
            if exc.response.status_code != 404:
                return None, f"Last.fm returned HTTP {exc.response.status_code}."
            return None, None
        except (httpx.HTTPError, ValueError, TypeError, AttributeError) as exc:
            return None, f"{type(exc).__name__}: Last.fm lookup failed."
