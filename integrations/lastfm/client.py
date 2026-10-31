"""Rate-limited, cached Last.fm HTTP client used by discovery services."""
from __future__ import annotations

import hashlib
import json
import threading
import time
from collections.abc import Callable, Mapping
from typing import Any

import httpx

from recommendation_run_metrics import record_provider_call, timed_stage

from recommendation.music_key import music_key


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

    @staticmethod
    def _call_cache_key(method: str, params: Mapping[str, Any]) -> str:
        cache_identity = json.dumps(
            {"method": method, "params": dict(params)},
            sort_keys=True,
            ensure_ascii=False,
        )
        return "discovery:lastfm:" + hashlib.sha256(
            cache_identity.encode("utf-8")
        ).hexdigest()

    def cached_album_popularity(
        self, artist: str, album: str, top_albums_limit: int = 8
    ) -> dict[str, int] | None:
        """Return Last.fm listeners/playcount for an album from the cache only; never calls the API.

        Looks in the album.getInfo cache first, then in the cached artist top-albums list that
        the Classics and Deep Dives builds already fill. None when neither holds the album.
        """
        if not artist or not album:
            return None
        week = 30 * 24 * 60 * 60
        cached = self._cache_get(
            "lastfm:album-info-v2:" + self._key_normalizer(artist) + ":" + self._key_normalizer(album), week
        )
        if isinstance(cached, dict) and cached.get("listeners") is not None:
            return {"listeners": int(cached["listeners"]), "playcount": int(cached.get("playcount") or 0)}
        payload = self._cache_get(
            self._call_cache_key("artist.getTopAlbums", {"artist": artist, "limit": top_albums_limit}), week
        )
        if isinstance(payload, dict):
            wanted = self._key_normalizer(album)
            for record in self._items_normalizer((payload.get("topalbums") or {}).get("album")):
                if isinstance(record, dict) and self._key_normalizer(record.get("name") or "") == wanted:
                    return {"listeners": int(record.get("listeners") or 0), "playcount": int(record.get("playcount") or 0)}
        return None

    def cached_call(self, method: str, ttl_seconds: int = 30 * 24 * 60 * 60, **params: Any) -> Any:
        """Return cached provider data or fetch it with the existing pacing policy."""
        api_key = str(self._settings_reader().get("lastfm_api_key") or "").strip()
        if not api_key:
            return None
        cache_key = self._call_cache_key(method, params)
        cached = self._cache_get(cache_key, ttl_seconds)
        if cached is not None:
            return cached
        try:
            with self._request_lock:
                wait = 0.2 - (self._monotonic() - self._last_request_at)
                if wait > 0:
                    self._sleep(wait)
                self._last_request_at = self._monotonic()
            record_provider_call("lastfm", "api")
            response = self._http_get(
                "https://ws.audioscrobbler.com/2.0/",
                params={
                    "method": method,
                    "api_key": api_key,
                    "format": "json",
                    "autocorrect": 1,
                    **params,
                },
                headers={"User-Agent": "Discair/1.0"},
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


    def artist_top_albums(self, artist: str, limit: int = 8) -> list[dict[str, Any]]:
        """Return normalized Last.fm top-album records for one artist."""
        payload = self.cached_call(
            "artist.getTopAlbums",
            ttl_seconds=30 * 24 * 60 * 60,
            artist=artist,
            limit=limit,
        )
        if not payload:
            return []
        records = self._items_normalizer((payload.get("topalbums") or {}).get("album"))
        output = []
        for album in records:
            if not isinstance(album, dict):
                continue
            title = str(album.get("name") or "").strip()
            if not title:
                continue
            output.append({
                "artist": artist,
                "album": title,
                "mbid": album.get("mbid") or None,
                "lastfm_listeners": int(album.get("listeners") or 0),
                "lastfm_playcount": int(album.get("playcount") or 0),
                "lastfm_url": album.get("url"),
            })
        return output


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


    def similar_artists(self, artist: str, limit: int = 8) -> list[dict[str, Any]]:
        """Return Last.fm similar-artist names and normalized similarity scores."""
        payload = self.cached_call(
            "artist.getSimilar",
            ttl_seconds=60 * 24 * 60 * 60,
            artist=artist,
            limit=limit,
        )
        if not payload:
            return []
        records = self._items_normalizer((payload.get("similarartists") or {}).get("artist"))
        output = []
        for item in records:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            if not name:
                continue
            try:
                match = float(item.get("match") or 0)
            except (ValueError, TypeError):
                match = 0.0
            output.append({"artist": name, "similarity": match})
        return output


    @timed_stage('lastfm_album_popularity')
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
            record_provider_call("lastfm", "api")
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
                headers={"User-Agent": "Discair/1.0"},
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
