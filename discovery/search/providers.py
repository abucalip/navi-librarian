"""External text-search clients for global search (contract sections 5.1 and 9).

Each call returns neutral candidate records. Ownership, dedupe and result shaping happen
in ``discovery/search/merge.py``. A failure raises ``ProviderError`` with the source state
the contract reports (``failed`` or ``rate_limited``); the runner maps a deadline to ``timeout``.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from discovery.search.cache import DEPTH
from discovery.search.limiter import SourceLimiter
from discovery.search.normalize import normalize_key

MUSICBRAINZ = "musicbrainz"
LASTFM = "lastfm"

MB_BASE = "https://musicbrainz.org/ws/2"
LASTFM_BASE = "https://ws.audioscrobbler.com/2.0/"
MB_HEADERS = {
    "User-Agent": "NavidromeLibrarian/1.0 (personal music discovery; contact: local app)",
    "Accept": "application/json",
}
# Pause before each retry after a MusicBrainz 503 (section 9: backoff and retry are required).
MB_RETRY_DELAYS = (1.0, 2.0)
MIN_TIMEOUT = 0.5
MAX_TIMEOUT = 5.0


class ProviderError(Exception):
    """A provider call that did not produce results. ``state`` is the reported source state."""

    def __init__(self, state: str):
        super().__init__(state)
        self.state = state


def lucene_phrase(text: str) -> str:
    """Quote ``text`` as one Lucene phrase, escaping only what a phrase needs."""
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _year(value: Any) -> int | None:
    text = str(value or "")[:4]
    return int(text) if text.isdigit() and 1000 <= int(text) <= 2100 else None


def _credit_name(credit: Any) -> str:
    """Join a MusicBrainz artist-credit list into the display name, as MusicBrainz does."""
    if not isinstance(credit, list):
        return ""
    parts = []
    for item in credit:
        if not isinstance(item, dict):
            continue
        name = item.get("name") or (item.get("artist") or {}).get("name") or ""
        parts.append(str(name) + str(item.get("joinphrase") or ""))
    return "".join(parts).strip()


def artist_candidate(source: str, name: str, mbid: str | None) -> dict[str, Any]:
    return {
        "type": "artist",
        "source": source,
        "name": name,
        "key": normalize_key(name),
        "mbid": mbid or None,
        "artist": None,
        "artist_key": None,
        "year": None,
        "release_group_mbid": None,
    }


def album_candidate(
    source: str,
    title: str,
    artist: str,
    year: int | None,
    release_group_mbid: str | None,
) -> dict[str, Any]:
    artist_key = normalize_key(artist)
    return {
        "type": "album",
        "source": source,
        "name": title,
        "key": f"{artist_key}/{normalize_key(title)}",
        "mbid": None,
        "artist": artist,
        "artist_key": artist_key,
        "year": year,
        "release_group_mbid": release_group_mbid or None,
    }


def _usable(candidate: dict[str, Any]) -> bool:
    """Drop records whose key would be empty; they cannot be matched or shown."""
    return bool(candidate["key"]) and bool(candidate["name"])


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


class MusicBrainzSearch:
    """MusicBrainz artist and release-group search, paced by the shared limiter."""

    source = MUSICBRAINZ

    def __init__(
        self,
        *,
        get: Callable[..., Any],
        limiter: SourceLimiter,
        pause: Callable[[float], None] = time.sleep,
    ):
        self._get = get
        self._limiter = limiter
        self._pause = pause

    def _request(self, path: str, params: dict[str, Any], *, remaining, cancelled) -> dict[str, Any]:
        for delay in (0.0, *MB_RETRY_DELAYS):
            if cancelled.is_set():
                raise ProviderError("failed")
            if delay:
                self._pause(delay)
            if not self._limiter.admit(self.source, remaining()):
                raise ProviderError("rate_limited")
            response = self._get(
                f"{MB_BASE}{path}",
                params={**params, "fmt": "json"},
                headers=MB_HEADERS,
                timeout=min(MAX_TIMEOUT, max(MIN_TIMEOUT, remaining())),
            )
            if response.status_code == 503:
                continue
            response.raise_for_status()
            return response.json()
        raise ProviderError("failed")

    def artists(self, query: str, *, remaining, cancelled) -> list[dict[str, Any]]:
        payload = self._request(
            "/artist",
            {"query": f"artist:{lucene_phrase(query)}", "limit": DEPTH},
            remaining=remaining,
            cancelled=cancelled,
        )
        candidates = [
            artist_candidate(self.source, str(item.get("name") or "").strip(), item.get("id"))
            for item in _as_list(payload.get("artists"))
            if isinstance(item, dict) and item.get("id")
        ]
        return [c for c in candidates if _usable(c)]

    def albums(self, query: str, *, remaining, cancelled) -> list[dict[str, Any]]:
        payload = self._request(
            "/release-group",
            {
                "query": f"releasegroup:{lucene_phrase(query)} AND primarytype:album",
                "limit": DEPTH,
            },
            remaining=remaining,
            cancelled=cancelled,
        )
        candidates = []
        for item in _as_list(payload.get("release-groups")):
            if not isinstance(item, dict) or not item.get("id"):
                continue
            candidates.append(album_candidate(
                self.source,
                str(item.get("title") or "").strip(),
                _credit_name(item.get("artist-credit")),
                _year(item.get("first-release-date")),
                item.get("id"),
            ))
        return [c for c in candidates if _usable(c) and c["artist"]]


class LastFmSearch:
    """Last.fm text search. Needs the saved API key; the caller checks it before any call."""

    source = LASTFM

    def __init__(
        self,
        *,
        get: Callable[..., Any],
        limiter: SourceLimiter,
        api_key: str,
    ):
        self._get = get
        self._limiter = limiter
        self._api_key = api_key

    def _call(self, method: str, params: dict[str, Any], *, remaining, cancelled) -> dict[str, Any]:
        if cancelled.is_set():
            raise ProviderError("failed")
        if not self._limiter.admit(self.source, remaining()):
            raise ProviderError("rate_limited")
        response = self._get(
            LASTFM_BASE,
            params={"method": method, "api_key": self._api_key, "format": "json", "limit": DEPTH, **params},
            headers={"User-Agent": MB_HEADERS["User-Agent"]},
            timeout=min(MAX_TIMEOUT, max(MIN_TIMEOUT, remaining())),
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict) or payload.get("error"):
            # Last.fm reports errors inside an HTTP 200 body; those are failures, not empty answers.
            raise ProviderError("failed")
        return payload

    def artists(self, query: str, *, remaining, cancelled) -> list[dict[str, Any]]:
        payload = self._call("artist.search", {"artist": query}, remaining=remaining, cancelled=cancelled)
        matches = _as_list(((payload.get("results") or {}).get("artistmatches") or {}).get("artist"))
        candidates = [
            artist_candidate(self.source, str(item.get("name") or "").strip(), item.get("mbid"))
            for item in matches
            if isinstance(item, dict)
        ]
        return [c for c in candidates if _usable(c)]

    def albums(self, query: str, *, remaining, cancelled) -> list[dict[str, Any]]:
        payload = self._call("album.search", {"album": query}, remaining=remaining, cancelled=cancelled)
        matches = _as_list(((payload.get("results") or {}).get("albummatches") or {}).get("album"))
        candidates = [
            album_candidate(
                self.source,
                str(item.get("name") or "").strip(),
                str(item.get("artist") or "").strip(),
                None,
                None,
            )
            for item in matches
            if isinstance(item, dict)
        ]
        return [c for c in candidates if _usable(c) and c["artist"]]
