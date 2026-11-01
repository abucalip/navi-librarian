"""Exact-match MusicBrainz release-year lookup with bounded cache and request pacing."""
from __future__ import annotations

import json
import threading
from time import monotonic, sleep
from urllib.parse import urlencode
from urllib.request import Request, urlopen

YEAR_CACHE_TTL = 180 * 24 * 60 * 60
year_cache = {}
_year_lock = threading.Lock()
_last_request = 0.0


def _norm(value):
    return "".join(ch.casefold() for ch in str(value or "") if ch.isalnum())


def _exact_year(groups, artist: str, album: str):
    """Earliest first-release year among groups whose title and artist credit match exactly."""
    exact_dates = []
    for group in groups:
        if _norm(group.get("title")) != _norm(album):
            continue
        credits = []
        for part in group.get("artist-credit") or []:
            if not isinstance(part, dict):
                continue
            credit_name = (part.get("artist") or {}).get("name") or part.get("name")
            if credit_name:
                credits.append(str(credit_name))
        if _norm(artist) not in {_norm(name) for name in credits} and _norm("".join(credits)) != _norm(artist):
            continue
        date_text = str(group.get("first-release-date") or "")
        year_text = date_text[:4]
        if year_text.isdigit() and 1900 <= int(year_text) <= 2100:
            exact_dates.append((date_text or year_text, int(year_text)))
    return min(exact_dates, key=lambda entry: entry[0])[1] if exact_dates else None


def lookup_album_year(artist: str, album: str):
    """Resolve a release year only for an exact title and artist-credit match."""
    global _last_request

    norm = _norm
    artist = str(artist or "").strip()
    album = str(album or "").strip()
    if not artist or not album:
        return None
    key = (norm(artist), norm(album))
    now = monotonic()
    cached = year_cache.get(key)
    if cached:
        ttl = YEAR_CACHE_TTL if cached.get("year") else 6 * 60 * 60
        if now - cached["time"] < ttl:
            return cached["year"]

    year = None
    try:
        with _year_lock:
            cached = year_cache.get(key)
            now = monotonic()
            if cached:
                ttl = YEAR_CACHE_TTL if cached.get("year") else 6 * 60 * 60
                if now - cached["time"] < ttl:
                    return cached["year"]
            wait = 1.1 - (now - _last_request)
            if wait > 0:
                sleep(wait)
            escaped_artist = artist.replace("\\\\", "\\\\\\\\").replace('"', '\\"')
            escaped_album = album.replace("\\\\", "\\\\\\\\").replace('"', '\\"')
            query = urlencode({
                "query": f'artist:"{escaped_artist}" AND releasegroup:"{escaped_album}"',
                "fmt": "json",
                "limit": 25,
            })
            request = Request(
                "https://musicbrainz.org/ws/2/release-group/?" + query,
                headers={"User-Agent": "Discair/1.0 (personal music discovery)"},
            )
            _last_request = monotonic()
            with urlopen(request, timeout=8) as response:
                payload = json.loads(response.read().decode("utf-8"))

        year = _exact_year(payload.get("release-groups") or [], artist, album)
    except Exception:
        # Metadata is optional; catalog/network errors remain non-fatal.
        pass

    year_cache[key] = {"time": monotonic(), "year": year}
    return year


# One MusicBrainz search can OR several artist/album queries, so a page of albums needs a handful
# of requests instead of one each. 15 pairs keep the URL near 1.3 KB.
BATCH_PAIR_LIMIT = 15
BATCH_RESULT_LIMIT = 100
BATCH_RETRY_PAUSE = 3.0


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _fetch_release_groups(query: str, limit: int):
    request = Request(
        "https://musicbrainz.org/ws/2/release-group/?"
        + urlencode({"query": query, "fmt": "json", "limit": limit}),
        headers={"User-Agent": "Discair/1.0 (personal music discovery)"},
    )
    with urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8")).get("release-groups") or []


def lookup_album_years(pairs, fetch=_fetch_release_groups):
    """Resolve many (artist, album) pairs with few MusicBrainz requests.

    Returns {(artist, album): year or None} for every usable pair given. Cached pairs cost no
    request. A request that fails leaves its pairs out of the result and out of the cache, so a
    later call retries them; a pair absent from a complete response is cached as no year, as the
    single lookup does. A response filled to the result limit is incomplete, so its chunk is split
    and re-queried rather than trusted. Same exact title and artist-credit rule, same pacing lock.
    """
    global _last_request
    results = {}
    missing = []
    for artist, album in pairs:
        artist = str(artist or "").strip()
        album = str(album or "").strip()
        if not artist or not album:
            continue
        key = (_norm(artist), _norm(album))
        cached = year_cache.get(key)
        if cached:
            ttl = YEAR_CACHE_TTL if cached.get("year") else 6 * 60 * 60
            if monotonic() - cached["time"] < ttl:
                results[(artist, album)] = cached["year"]
                continue
        missing.append((artist, album))

    def resolve(chunk):
        global _last_request
        query = " OR ".join(
            f'(artist:"{_escape(artist)}" AND releasegroup:"{_escape(album)}")' for artist, album in chunk
        )
        groups = None
        # MusicBrainz answers 503 when requests run over its rate limit; one retry after a pause.
        for attempt in range(2):
            try:
                with _year_lock:
                    wait = (1.1 if attempt == 0 else BATCH_RETRY_PAUSE) - (monotonic() - _last_request)
                    if wait > 0:
                        sleep(wait)
                    _last_request = monotonic()
                    groups = fetch(query, BATCH_RESULT_LIMIT)
                break
            except Exception:
                groups = None
        if groups is None:
            return
        if len(groups) >= BATCH_RESULT_LIMIT and len(chunk) > 1:
            # A capped response may have dropped a valid match, so absence proves nothing:
            # split the chunk until each half is answered in full.
            middle = len(chunk) // 2
            resolve(chunk[:middle])
            resolve(chunk[middle:])
            return
        for artist, album in chunk:
            year = _exact_year(groups, artist, album)
            year_cache[(_norm(artist), _norm(album))] = {"time": monotonic(), "year": year}
            results[(artist, album)] = year

    for start in range(0, len(missing), BATCH_PAIR_LIMIT):
        resolve(missing[start:start + BATCH_PAIR_LIMIT])
    return results
