"""Rate-limited, cached Last.fm HTTP client used by discovery services."""
from __future__ import annotations

import hashlib
import json
import threading
import time
from collections.abc import Callable, Mapping
from typing import Any

import httpx


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
    ):
        self._settings_reader = settings_reader
        self._cache_get = cache_get
        self._cache_set = cache_set
        self._http_get = http_get or httpx.get
        self._monotonic = monotonic or time.monotonic
        self._sleep = sleep or time.sleep
        self._request_lock = request_lock or threading.Lock()
        self._last_request_at = 0.0

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
