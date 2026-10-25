"""External text-search clients for global search (contract sections 5.1 and 9).

Each call returns neutral candidate records. Ownership, dedupe and result shaping happen
in ``discovery/search/merge.py``. A failure raises ``ProviderError`` with the source state
the contract reports (``failed`` or ``rate_limited``); the runner maps a deadline to ``timeout``.
"""

from __future__ import annotations

import re
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
# MusicBrainz browse calls accept up to 100 results per page.
BROWSE_LIMIT = 100
# Batched identity lookup (section 9): up to 100 names and about 1800 characters of query per call.
# The URL length limit, not the name count, is what decides the batch size.
IDENTITY_BATCH_NAMES = 100
IDENTITY_BATCH_CHARS = 1800
IDENTITY_MAX_PAGES = 5
# Each HTTP request has this fixed budget. It is not derived from the search deadline, because a
# shared call can gain later consumers (and so a later deadline) after its request has started.
# Consumers stop waiting at their own deadlines; a request in flight is discarded when it returns.
REQUEST_TIMEOUT = 5.0


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
                timeout=REQUEST_TIMEOUT,
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


    def artist_identities(self, names: list[str], *, remaining, cancelled) -> dict[str, str]:
        """MBIDs for many artist names, found with OR queries of up to 100 names each.

        Returns ``{normalized key: MBID}`` for exact key matches only. The first match in
        MusicBrainz's own ranking wins. A name whose match is not on the first
        ``IDENTITY_MAX_PAGES`` pages stays unresolved. Each page is one request.
        """
        wanted: dict[str, str] = {}
        for name in names:
            key = normalize_key(name)
            if key and key not in wanted:
                wanted[key] = name
        found: dict[str, str] = {}
        for batch in _identity_batches(wanted):
            keys = {normalize_key(name) for name in batch}
            query = " OR ".join(f"artist:{lucene_phrase(name)}" for name in batch)
            for page in range(IDENTITY_MAX_PAGES):
                payload = self._request(
                    "/artist",
                    {"query": query, "limit": IDENTITY_BATCH_NAMES, "offset": page * IDENTITY_BATCH_NAMES},
                    remaining=remaining,
                    cancelled=cancelled,
                )
                for item in _as_list(payload.get("artists")):
                    if not isinstance(item, dict) or not item.get("id"):
                        continue
                    key = normalize_key(item.get("name"))
                    if key in keys and key not in found:
                        found[key] = item["id"]
                fetched = (page + 1) * IDENTITY_BATCH_NAMES
                if keys.issubset(found) or fetched >= int(payload.get("count") or 0):
                    break
        return found

    def release_groups_for_releases(self, release_ids: list[str], *, remaining, cancelled) -> dict[str, str]:
        """Release-group MBID for each release MBID, in OR batches. Malformed IDs are skipped."""
        valid = list(dict.fromkeys(rid for rid in release_ids if _RELEASE_ID.fullmatch(rid or "")))
        found: dict[str, str] = {}
        for batch in _term_batches([(rid, f"reid:{rid}") for rid in valid]):
            wanted = {rid for rid, _ in batch}
            query = " OR ".join(term for _, term in batch)
            for page in range(IDENTITY_MAX_PAGES):
                payload = self._request(
                    "/release",
                    {"query": query, "limit": IDENTITY_BATCH_NAMES, "offset": page * IDENTITY_BATCH_NAMES},
                    remaining=remaining,
                    cancelled=cancelled,
                )
                for item in _as_list(payload.get("releases")):
                    if not isinstance(item, dict):
                        continue
                    rid = item.get("id")
                    group = (item.get("release-group") or {}).get("id")
                    if rid in wanted and group and rid not in found:
                        found[rid] = group
                fetched = (page + 1) * IDENTITY_BATCH_NAMES
                if wanted.issubset(found) or fetched >= int(payload.get("count") or 0):
                    break
        return found

    def album_identities(
        self,
        albums: list[tuple[str, str, int | None]],
        *,
        remaining,
        cancelled,
    ) -> dict[tuple[str, str], str]:
        """Release-group MBID for (artist, title, year) triples, in OR batches.

        Returns ``{(artist key, album key): MBID}``. Only exact key matches count. When several
        matches exist, the first one whose year agrees (or is unknown) wins; otherwise the first.
        """
        wanted: dict[tuple[str, str], tuple[str, str, int | None]] = {}
        for artist, title, year in albums:
            key = (normalize_key(artist), normalize_key(title))
            if key[0] and key[1] and key not in wanted:
                wanted[key] = (artist, title, year)
        found: dict[tuple[str, str], str] = {}
        year_agrees: set[tuple[str, str]] = set()
        terms = [
            (key, f"(releasegroup:{lucene_phrase(title)} AND artist:{lucene_phrase(artist)} AND primarytype:album)")
            for key, (artist, title, _) in wanted.items()
        ]
        for batch in _term_batches(terms):
            keys = {key for key, _ in batch}
            query = " OR ".join(term for _, term in batch)
            for page in range(IDENTITY_MAX_PAGES):
                payload = self._request(
                    "/release-group",
                    {"query": query, "limit": IDENTITY_BATCH_NAMES, "offset": page * IDENTITY_BATCH_NAMES},
                    remaining=remaining,
                    cancelled=cancelled,
                )
                for item in _as_list(payload.get("release-groups")):
                    if not isinstance(item, dict) or not item.get("id"):
                        continue
                    key = (
                        normalize_key(_credit_name(item.get("artist-credit"))),
                        normalize_key(item.get("title")),
                    )
                    if key not in keys:
                        continue
                    wanted_year = wanted[key][2]
                    year = _year(item.get("first-release-date"))
                    agrees = wanted_year is None or year is None or year == wanted_year
                    if key not in found or (agrees and key not in year_agrees):
                        found[key] = item["id"]
                        if agrees:
                            year_agrees.add(key)
                fetched = (page + 1) * IDENTITY_BATCH_NAMES
                if keys.issubset(found) or fetched >= int(payload.get("count") or 0):
                    break
        return found

    def albums_by_artist(self, artist_mbid: str, *, remaining, cancelled) -> list[dict[str, Any]]:
        """Studio albums of one artist (primary type album, no secondary types such as live or compilation)."""
        payload = self._request(
            "/release-group",
            {"artist": artist_mbid, "type": "album", "limit": BROWSE_LIMIT},
            remaining=remaining,
            cancelled=cancelled,
        )
        candidates = []
        for item in _as_list(payload.get("release-groups")):
            if not isinstance(item, dict) or not item.get("id") or item.get("secondary-types"):
                continue
            candidates.append(album_candidate(
                self.source,
                str(item.get("title") or "").strip(),
                _credit_name(item.get("artist-credit")),
                _year(item.get("first-release-date")),
                item.get("id"),
            ))
        return [c for c in candidates if _usable(c) and c["artist"]]


_RELEASE_ID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def _term_batches(items: list[tuple[str, str]]):
    """Yield lists of ``(key, term)`` under the name and character limits of one OR query."""
    batch: list[tuple[str, str]] = []
    size = 0
    for key, term in items:
        cost = len(term) + len(" OR ")
        if batch and (len(batch) >= IDENTITY_BATCH_NAMES or size + cost > IDENTITY_BATCH_CHARS):
            yield batch
            batch, size = [], 0
        batch.append((key, term))
        size += cost
    if batch:
        yield batch


def _identity_batches(wanted: dict[str, str]):
    """Yield lists of names, each under the name and character limits."""
    batch: list[str] = []
    size = 0
    for name in wanted.values():
        term = len(f"artist:{lucene_phrase(name)} OR ")
        if batch and (len(batch) >= IDENTITY_BATCH_NAMES or size + term > IDENTITY_BATCH_CHARS):
            yield batch
            batch, size = [], 0
        batch.append(name)
        size += term
    if batch:
        yield batch


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
            timeout=REQUEST_TIMEOUT,
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

    def top_albums(self, artist_name: str, *, remaining, cancelled) -> list[dict[str, Any]]:
        """Last.fm's top albums for one artist. Used on the artist page, not in search."""
        payload = self._call("artist.getTopAlbums", {"artist": artist_name}, remaining=remaining, cancelled=cancelled)
        albums = _as_list((payload.get("topalbums") or {}).get("album"))
        candidates = [
            album_candidate(self.source, str(item.get("name") or "").strip(), artist_name, None, None)
            for item in albums
            if isinstance(item, dict)
        ]
        return [c for c in candidates if _usable(c)]
