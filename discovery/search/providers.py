"""External text-search clients for global search (contract sections 5.1 and 9).

Each call returns neutral candidate records. Ownership, dedupe and result shaping happen
in ``discovery/search/merge.py``. A failure raises ``ProviderError`` with the source state
the contract reports (``failed`` or ``rate_limited``); the runner maps a deadline to ``timeout``.
"""

from __future__ import annotations

import html
import re
import time
from collections.abc import Callable
from typing import Any
from urllib.parse import quote

from discovery.search.cache import DEPTH
from discovery.search.limiter import SourceLimiter
from discovery.search.normalize import normalize_key

MUSICBRAINZ = "musicbrainz"
LASTFM = "lastfm"
LISTENBRAINZ = "listenbrainz"
DISCOGS = "discogs"

MB_BASE = "https://musicbrainz.org/ws/2"
LASTFM_BASE = "https://ws.audioscrobbler.com/2.0/"
DISCOGS_BASE = "https://api.discogs.com"
DISCOGS_ATTRIBUTION = "Data provided by Discogs"
MB_HEADERS = {
    "User-Agent": "Discair/1.0 (personal music discovery; contact: local app)",
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


def genre_candidate(source: str, name: str) -> dict[str, Any]:
    """A genre or style name. The key doubles as the normalized tag (contract section 3.8)."""
    return {
        "type": "genre",
        "source": source,
        "name": name,
        "key": normalize_key(name),
        "mbid": None,
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
        request_timeout: float = REQUEST_TIMEOUT,
    ):
        self._get = get
        self._limiter = limiter
        self._pause = pause
        self._request_timeout = request_timeout

    def _request(self, path: str, params: dict[str, Any], *, remaining, cancelled, raw: bool = False) -> Any:
        for delay in (0.0, *MB_RETRY_DELAYS):
            if cancelled.is_set():
                raise ProviderError("failed")
            if delay:
                if remaining() <= delay:
                    # Throttled, and the backoff cannot fit in the deadline: report it now and let the
                    # search finish with the other sources' results instead of waiting for a timeout.
                    raise ProviderError("rate_limited")
                self._pause(delay)
            if not self._limiter.admit(self.source, remaining()):
                raise ProviderError("rate_limited")
            try:
                response = self._get(
                    f"{MB_BASE}{path}",
                    params={**params, "fmt": "txt" if raw else "json"},
                    headers=MB_HEADERS,
                    timeout=self._request_timeout,
                )
            except Exception as exc:
                # A timeout or connection error is a failed call, so callers can skip just this request.
                raise ProviderError("failed") from exc
            if response.status_code == 503:
                continue
            response.raise_for_status()
            return response.text if raw else response.json()
        raise ProviderError("failed")

    def genre_names(self, *, remaining, cancelled) -> list[str]:
        """Every MusicBrainz genre name, from the one-request plain-text list (MusicBrainz has no genre search)."""
        text = self._request("/genre/all", {}, remaining=remaining, cancelled=cancelled, raw=True)
        names = [line.strip() for line in str(text).splitlines() if line.strip()]
        if not names:
            # An empty list is a failed answer, not "no genres": it must never be cached.
            raise ProviderError("failed")
        return names

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


    def artists_by_tag(self, tag: str, *, remaining, cancelled) -> list[dict[str, Any]]:
        """Artists carrying a community tag, best match first (genre pages)."""
        payload = self._request(
            "/artist",
            {"query": f"tag:{lucene_phrase(tag)}", "limit": DEPTH},
            remaining=remaining,
            cancelled=cancelled,
        )
        candidates = [
            artist_candidate(self.source, str(item.get("name") or "").strip(), item.get("id"))
            for item in _as_list(payload.get("artists"))
            if isinstance(item, dict) and item.get("id")
        ]
        return [c for c in candidates if _usable(c)]

    def albums_by_tag(self, tag: str, *, remaining, cancelled) -> list[dict[str, Any]]:
        """Studio albums carrying a community tag, best match first (genre pages)."""
        payload = self._request(
            "/release-group",
            {"query": f"tag:{lucene_phrase(tag)} AND primarytype:album", "limit": DEPTH},
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

    def artist_tags(self, artist_mbid: str, *, remaining, cancelled) -> list[dict[str, Any]]:
        """Community tags of one artist, lower-cased, with their vote counts. Used for shared-tag similarity."""
        payload = self._request(
            f"/artist/{quote(artist_mbid, safe='')}",
            {"inc": "tags"},
            remaining=remaining,
            cancelled=cancelled,
        )
        output = []
        for item in _as_list(payload.get("tags")):
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip().casefold()
            if name and int(item.get("count") or 0) >= 1:
                output.append({"name": name})
        return output

    def release_group_tracks(self, release_group_mbid: str, *, remaining, cancelled) -> list[dict[str, Any]]:
        """Tracks of the first official release in one release group (two requests)."""
        group = self._request(
            f"/release-group/{quote(release_group_mbid, safe='')}",
            {"inc": "releases"},
            remaining=remaining,
            cancelled=cancelled,
        )
        releases = [r for r in _as_list(group.get("releases")) if isinstance(r, dict) and r.get("id")]
        releases.sort(key=lambda r: (r.get("status") != "Official", str(r.get("date") or "9999")))
        if not releases:
            return []
        release = self._request(
            f"/release/{quote(releases[0]['id'], safe='')}",
            {"inc": "recordings"},
            remaining=remaining,
            cancelled=cancelled,
        )
        output: list[dict[str, Any]] = []
        for medium in _as_list(release.get("media")):
            if not isinstance(medium, dict):
                continue
            for track in _as_list(medium.get("tracks")):
                title = str(track.get("title") or "").strip() if isinstance(track, dict) else ""
                if title:
                    length = track.get("length")
                    output.append({
                        "track_number": len(output) + 1,
                        "title": title,
                        "duration_seconds": int(length // 1000) if isinstance(length, (int, float)) else 0,
                    })
        return output

    def release_groups_named(self, artist: str, album: str, *, remaining, cancelled) -> list[dict[str, Any]]:
        """Raw release-group results for an exact artist and title query (used to link an album's own page)."""
        payload = self._request(
            "/release-group",
            {"query": f"releasegroup:{lucene_phrase(album)} AND artist:{lucene_phrase(artist)}", "limit": 5},
            remaining=remaining,
            cancelled=cancelled,
        )
        return [g for g in _as_list(payload.get("release-groups")) if isinstance(g, dict)]

    def albums_by_artist(self, artist_mbid: str, *, remaining, cancelled) -> list[dict[str, Any]]:
        """Studio albums of one artist (primary type album, no secondary types such as live or compilation).

        This is a search, not a browse: a browse returns release groups in no useful order, and an
        artist with hundreds of live recordings fills its first page with them and shows no albums.
        """
        payload = self._request(
            "/release-group",
            {"query": f"arid:{artist_mbid} AND primarytype:album AND NOT secondarytype:*", "limit": BROWSE_LIMIT},
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

    def similar(self, artist_name: str, *, remaining, cancelled) -> list[dict[str, Any]]:
        """Last.fm's similar artists, best first, with the match score (0 to 1) it reports."""
        payload = self._call("artist.getSimilar", {"artist": artist_name}, remaining=remaining, cancelled=cancelled)
        matches = _as_list((payload.get("similarartists") or {}).get("artist"))
        output = []
        for item in matches:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            if not name:
                continue
            try:
                match = float(item.get("match") or 0)
            except (TypeError, ValueError):
                match = 0.0
            output.append({
                "name": name,
                "mbid": str(item.get("mbid") or "").strip() or None,
                "match": min(max(match, 0.0), 1.0),
            })
        return output

    def artist_bio(self, artist_name: str, *, remaining, cancelled) -> str | None:
        """Last.fm's biography of an artist as plain text (the source Navidrome's own bios usually come from)."""
        payload = self._call("artist.getInfo", {"artist": artist_name}, remaining=remaining, cancelled=cancelled)
        content = str(((payload.get("artist") or {}).get("bio") or {}).get("content") or "")
        text = re.sub(r"<a\b[^>]*>.*?</a>", "", content, flags=re.S | re.I)
        text = re.sub(r"<[^>]+>", "", text)
        return re.sub(r"\s+", " ", html.unescape(text)).strip() or None

    def album_tracks(self, artist_name: str, album_name: str, *, remaining, cancelled) -> list[dict[str, Any]]:
        """Last.fm's tracklist for one album (one request)."""
        payload = self._call(
            "album.getInfo", {"artist": artist_name, "album": album_name},
            remaining=remaining, cancelled=cancelled,
        )
        output: list[dict[str, Any]] = []
        for item in _as_list(((payload.get("album") or {}).get("tracks") or {}).get("track")):
            title = str(item.get("name") or "").strip() if isinstance(item, dict) else ""
            if title:
                try:
                    seconds = int(item.get("duration") or 0)
                except (TypeError, ValueError):
                    seconds = 0
                output.append({"track_number": len(output) + 1, "title": title, "duration_seconds": seconds})
        return output

    def top_albums(self, artist_name: str, *, remaining, cancelled) -> list[dict[str, Any]]:
        """Last.fm's top albums for one artist. Used on the artist page, not in search."""
        payload = self._call("artist.getTopAlbums", {"artist": artist_name}, remaining=remaining, cancelled=cancelled)
        albums = _as_list((payload.get("topalbums") or {}).get("album"))
        candidates = []
        for item in albums:
            if not isinstance(item, dict):
                continue
            candidate = album_candidate(self.source, str(item.get("name") or "").strip(), artist_name, None, None)
            try:
                candidate["playcount"] = int(item.get("playcount") or 0) or None
            except (TypeError, ValueError):
                candidate["playcount"] = None
            candidates.append(candidate)
        return [c for c in candidates if _usable(c)]

    def top_tracks(self, artist_name: str, *, remaining, cancelled) -> list[dict[str, Any]]:
        """Last.fm's top tracks for one artist, most played first. Used on the artist page."""
        payload = self._call("artist.getTopTracks", {"artist": artist_name}, remaining=remaining, cancelled=cancelled)
        output: list[dict[str, Any]] = []
        for item in _as_list((payload.get("toptracks") or {}).get("track")):
            title = str(item.get("name") or "").strip() if isinstance(item, dict) else ""
            if not title:
                continue
            try:
                plays = int(item.get("playcount") or 0) or None
            except (TypeError, ValueError):
                plays = None
            output.append({
                "name": title,
                "listen_count": plays,
                "recording_mbid": str(item.get("mbid") or "").strip() or None,
                "album": None,
            })
        return output


LB_RADIO_BASE = "https://api.listenbrainz.org/1/lb-radio/artist"
LB_TOP_RECORDINGS_BASE = "https://api.listenbrainz.org/1/popularity/top-recordings-for-artist"
# The endpoint returns every recording (thousands); only the head matters for a top list.
LB_TOP_RECORDINGS_READ = 60
# Per the contract (section 7): five similar artists, one recording each, popularity unrestricted.
LB_RADIO_PARAMS = {"mode": "easy", "max_similar_artists": 5, "max_recordings_per_artist": 1, "pop_begin": 0, "pop_end": 100}


class ListenBrainzRadio:
    """ListenBrainz similar artists for one seed MBID. The result is ordered and has no score."""

    source = LISTENBRAINZ

    def __init__(self, *, get: Callable[..., Any], limiter: SourceLimiter, headers: dict[str, str]):
        self._get = get
        self._limiter = limiter
        self._headers = headers

    def similar(self, seed_mbid: str, *, remaining, cancelled) -> list[dict[str, Any]]:
        """Similar artists in the order ListenBrainz returns them. The seed is removed."""
        if cancelled.is_set():
            raise ProviderError("failed")
        if not self._limiter.admit(self.source, remaining()):
            raise ProviderError("rate_limited")
        response = self._get(
            f"{LB_RADIO_BASE}/{quote(seed_mbid, safe='')}",
            params=dict(LB_RADIO_PARAMS),
            headers=dict(self._headers),
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ProviderError("failed")
        output: list[dict[str, Any]] = []
        seen: set[str] = set()
        # The body is keyed by artist MBID; every value is a list of entries. Flatten in order.
        for entries in payload.values():
            for entry in _as_list(entries):
                if not isinstance(entry, dict):
                    continue
                mbid = str(entry.get("similar_artist_mbid") or "").strip()
                name = str(entry.get("similar_artist_name") or "").strip()
                if not mbid or not name or mbid == seed_mbid or mbid in seen:
                    continue
                seen.add(mbid)
                output.append({"name": name, "mbid": mbid, "match": None})
        return output

    def top_recordings(self, artist_mbid: str, *, remaining, cancelled) -> list[dict[str, Any]]:
        """ListenBrainz's most listened recordings for one artist MBID, most listened first."""
        if cancelled.is_set():
            raise ProviderError("failed")
        if not self._limiter.admit(self.source, remaining()):
            raise ProviderError("rate_limited")
        response = self._get(
            f"{LB_TOP_RECORDINGS_BASE}/{quote(artist_mbid, safe='')}",
            headers=dict(self._headers),
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            raise ProviderError("failed")
        output: list[dict[str, Any]] = []
        for entry in payload[:LB_TOP_RECORDINGS_READ]:
            title = str(entry.get("recording_name") or "").strip() if isinstance(entry, dict) else ""
            if not title:
                continue
            count = entry.get("total_listen_count")
            output.append({
                "name": title,
                "listen_count": int(count) if isinstance(count, (int, float)) else None,
                "recording_mbid": str(entry.get("recording_mbid") or "").strip() or None,
                "album": str(entry.get("release_name") or "").strip() or None,
            })
        return output


def _discogs_name(name: str) -> str:
    """An artist name without Discogs' disambiguation suffix, so "Ash (2)" reads "Ash"."""
    return re.sub(r"\s+\(\d+\)$", "", name.strip())


class DiscogsSearch:
    """Discogs styles and style browsing. Needs a personal access token; the caller checks it first.

    The token goes in the ``Authorization`` header only, never in a URL or a log line. Discogs
    answers 429 over the limit, which is reported as ``rate_limited``.
    """

    source = DISCOGS

    def __init__(self, *, get: Callable[..., Any], limiter: SourceLimiter, token: str):
        self._get = get
        self._limiter = limiter
        self._token = token

    def _search(self, params: dict[str, Any], *, remaining, cancelled) -> list[Any]:
        if cancelled.is_set():
            raise ProviderError("failed")
        if not self._limiter.admit(self.source, remaining()):
            raise ProviderError("rate_limited")
        try:
            response = self._get(
                f"{DISCOGS_BASE}/database/search",
                params={"type": "master", "per_page": DEPTH, **params},
                headers={
                    "Authorization": f"Discogs token={self._token}",
                    "User-Agent": MB_HEADERS["User-Agent"],
                },
                timeout=REQUEST_TIMEOUT,
            )
        except Exception as exc:
            raise ProviderError("failed") from exc
        if response.status_code == 429:
            raise ProviderError("rate_limited")
        try:
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            raise ProviderError("failed") from exc
        if not isinstance(payload, dict):
            raise ProviderError("failed")
        return _as_list(payload.get("results"))

    def _master_albums(self, params: dict[str, Any], *, remaining, cancelled) -> list[dict[str, Any]]:
        """Master releases as album candidates. Discogs titles read ``Artist - Album``."""
        candidates = []
        for item in self._search(params, remaining=remaining, cancelled=cancelled):
            if not isinstance(item, dict):
                continue
            artist, separator, title = str(item.get("title") or "").partition(" - ")
            if not separator:
                continue
            candidates.append(album_candidate(
                self.source, title.strip(), _discogs_name(artist), _year(item.get("year")), None,
            ))
        return [c for c in candidates if _usable(c) and c["artist"]]

    def style_albums(self, style: str, *, remaining, cancelled) -> list[dict[str, Any]]:
        """Master releases in one style as album candidates (genre pages)."""
        return self._master_albums({"style": style}, remaining=remaining, cancelled=cancelled)

    def albums(self, query: str, *, remaining, cancelled) -> list[dict[str, Any]]:
        """Master releases matching a text query (global search)."""
        return self._master_albums({"q": query}, remaining=remaining, cancelled=cancelled)

    def artists(self, query: str, *, remaining, cancelled) -> list[dict[str, Any]]:
        """Artists matching a text query (global search). Discogs has no MBIDs, so matching is by name."""
        candidates = []
        for item in self._search({"q": query, "type": "artist"}, remaining=remaining, cancelled=cancelled):
            if isinstance(item, dict):
                candidates.append(artist_candidate(self.source, _discogs_name(str(item.get("title") or "")), None))
        return [c for c in candidates if _usable(c)]

    def genres(self, query: str, *, remaining, cancelled) -> list[dict[str, Any]]:
        """Genres and styles named on the master releases a text query finds, when they contain the query.

        Discogs has no style search, so its published vocabulary is read off the search results.
        """
        wanted = normalize_key(query)
        names: dict[str, str] = {}
        for item in self._search({"q": query}, remaining=remaining, cancelled=cancelled):
            if not isinstance(item, dict):
                continue
            for value in [*_as_list(item.get("style")), *_as_list(item.get("genre"))]:
                name = str(value).strip()
                key = normalize_key(name)
                if key and wanted in key:
                    names.setdefault(key, name)
        return [genre_candidate(self.source, name) for name in names.values()]

    def artist_styles(self, name: str, *, remaining, cancelled) -> list[dict[str, Any]]:
        """Styles on the artist's master releases, lower-cased, most frequent first. Used for shared-style similarity."""
        key = normalize_key(name)
        counts: dict[str, int] = {}
        for item in self._search({"artist": name, "per_page": 25}, remaining=remaining, cancelled=cancelled):
            if not isinstance(item, dict):
                continue
            artist, separator, _ = str(item.get("title") or "").partition(" - ")
            if not separator or normalize_key(_discogs_name(artist)) != key:
                continue
            for style in _as_list(item.get("style")):
                folded = str(style).strip().casefold()
                if folded:
                    counts[folded] = counts.get(folded, 0) + 1
        return [{"name": style} for style in sorted(counts, key=lambda s: (-counts[s], s))]
