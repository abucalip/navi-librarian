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


def lookup_album_year(artist: str, album: str):
    """Resolve a release year only for an exact title and artist-credit match."""
    global _last_request

    def norm(value):
        return "".join(ch.casefold() for ch in str(value or "") if ch.isalnum())

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
                headers={"User-Agent": "NavidromeLibrarian/1.0 (personal music discovery)"},
            )
            _last_request = monotonic()
            with urlopen(request, timeout=8) as response:
                payload = json.loads(response.read().decode("utf-8"))

        exact_dates = []
        for group in payload.get("release-groups") or []:
            if norm(group.get("title")) != norm(album):
                continue
            credits = []
            for part in group.get("artist-credit") or []:
                if not isinstance(part, dict):
                    continue
                credit_name = (part.get("artist") or {}).get("name") or part.get("name")
                if credit_name:
                    credits.append(str(credit_name))
            if norm(artist) not in {norm(name) for name in credits} and norm("".join(credits)) != norm(artist):
                continue
            date_text = str(group.get("first-release-date") or "")
            year_text = date_text[:4]
            if year_text.isdigit() and 1900 <= int(year_text) <= 2100:
                exact_dates.append((date_text or year_text, int(year_text)))
        if exact_dates:
            year = min(exact_dates, key=lambda entry: entry[0])[1]
    except Exception:
        # Metadata is optional; catalog/network errors remain non-fatal.
        pass

    year_cache[key] = {"time": monotonic(), "year": year}
    return year
