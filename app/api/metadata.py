"""External metadata API routes and provider/cache helpers.

These endpoints enrich the UI with optional artist biographies, artwork, album
details, and release years. Provider failures remain non-fatal except for
invalid request parameters; discovery itself does not depend on metadata.
"""
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from time import monotonic, sleep
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException

from app.services.artist_bio import resolve_artist_bio
from urllib.request import urlopen

router = APIRouter()

_EXTERNAL_HTTP = httpx.Client(
    timeout=httpx.Timeout(3.0, connect=1.5),
    headers={"User-Agent": "NavidromeLibrarian/1.0 (personal music discovery; contact: local app)"},
)

# Artist biographies are cached for a day. Wikidata identifies the intended
# musical entity first; Wikipedia is only used when its page points back to
# that exact Wikidata item. This prevents name collisions (e.g. Rainbow the band
# versus the optical phenomenon) from producing unrelated summaries.
_ARTIST_BIO_CACHE_TTL = 24 * 60 * 60
_artist_bio_cache = {}

@router.get("/api/artist-bio")
def artist_bio(artist: str):
    name = str(artist or "").strip()
    if not name or len(name) > 180:
        raise HTTPException(status_code=400, detail="A valid artist name is required.")
    key = name.casefold()
    now = monotonic()
    cached = _artist_bio_cache.get(key)
    if cached and now - cached["time"] < _ARTIST_BIO_CACHE_TTL:
        return {"artist": name, "bio": cached["bio"]}

    bio = resolve_artist_bio(name, entities, page)

    _artist_bio_cache[key] = {"time": monotonic(), "bio": bio}
    return {"artist": name, "bio": bio}


# Artwork is optional presentation metadata; discovery works without it.
_ARTWORK_CACHE_TTL = 6 * 60 * 60
_ARTWORK_NEGATIVE_CACHE_TTL = 5 * 60
_artwork_cache = {}
_MUSICBRAINZ_YEAR_CACHE_TTL = 180 * 24 * 60 * 60
_musicbrainz_year_cache = {}
_musicbrainz_year_lock = threading.Lock()
_musicbrainz_last_request = 0.0


def _musicbrainz_album_year(artist: str, album: str):
    """Resolve a release year from an exact MusicBrainz release-group match."""
    import re
    global _musicbrainz_last_request

    def norm(value):
        return "".join(ch.casefold() for ch in str(value or "") if ch.isalnum())

    artist = str(artist or "").strip()
    album = str(album or "").strip()
    if not artist or not album:
        return None
    key = (norm(artist), norm(album))
    now = monotonic()
    cached = _musicbrainz_year_cache.get(key)
    if cached:
        ttl = _MUSICBRAINZ_YEAR_CACHE_TTL if cached.get("year") else 6 * 60 * 60
        if now - cached["time"] < ttl:
            return cached["year"]

    year = None
    try:
        with _musicbrainz_year_lock:
            cached = _musicbrainz_year_cache.get(key)
            now = monotonic()
            if cached:
                ttl = _MUSICBRAINZ_YEAR_CACHE_TTL if cached.get("year") else 6 * 60 * 60
                if now - cached["time"] < ttl:
                    return cached["year"]
            wait = 1.1 - (now - _musicbrainz_last_request)
            if wait > 0:
                sleep(wait)
            escaped_artist = artist.replace("\\", "\\\\").replace('"', '\\"')
            escaped_album = album.replace("\\", "\\\\").replace('"', '\\"')
            query = urlencode({
                "query": f'artist:"{escaped_artist}" AND releasegroup:"{escaped_album}"',
                "fmt": "json",
                "limit": 25,
            })
            request = __import__("urllib.request", fromlist=["Request"]).Request(
                "https://musicbrainz.org/ws/2/release-group/?" + query,
                headers={"User-Agent": "NavidromeLibrarian/1.0 (personal music discovery)"},
            )
            _musicbrainz_last_request = monotonic()
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
            # Accept an exact artist credit or an exact credited member of a
            # collaboration, never a substring such as "Queen Tribute".
            if norm(artist) not in {norm(name) for name in credits} and norm("".join(credits)) != norm(artist):
                continue
            date_text = str(group.get("first-release-date") or "")
            year_text = date_text[:4]
            if year_text.isdigit() and 1900 <= int(year_text) <= 2100:
                exact_dates.append((date_text or year_text, int(year_text)))
        if exact_dates:
            year = min(exact_dates, key=lambda entry: entry[0])[1]
    except Exception:
        # The UI can still show artwork; an unavailable catalog is not fatal.
        pass

    _musicbrainz_year_cache[key] = {"time": monotonic(), "year": year}
    return year


@router.get("/api/album-year")
def album_year(artist: str = "", album: str = ""):
    """Return a year only when an authoritative catalog has an exact album match."""
    artist = str(artist or "").strip()[:180]
    album = str(album or "").strip()[:180]
    if not artist or not album:
        raise HTTPException(status_code=400, detail="artist and album are required")

    year = _musicbrainz_album_year(artist, album)
    source = "MusicBrainz" if year else None

    # MusicBrainz is primary. Deezer is a fallback only for an exact normalized
    # artist AND album match; fuzzy or artist-only results are never trusted.
    if not year:
        def norm(value):
            return "".join(ch.casefold() for ch in str(value or "") if ch.isalnum())
        try:
            query = urlencode({"q": f'artist:"{artist}" album:"{album}"', "limit": 20})
            response = _EXTERNAL_HTTP.get("https://api.deezer.com/search/album?" + query)
            response.raise_for_status()
            for item in response.json().get("data") or []:
                if norm((item.get("artist") or {}).get("name")) != norm(artist):
                    continue
                if norm(item.get("title")) != norm(album):
                    continue
                year_text = str(item.get("release_date") or "")[:4]
                if year_text.isdigit() and 1900 <= int(year_text) <= 2100:
                    year = int(year_text)
                    source = "Deezer"
                    break
        except Exception:
            pass

    return {"artist": artist, "album": album, "year": year, "source": source}


@router.get("/api/album-details")
def album_details(artist: str = "", album: str = ""):
    """Return a carefully matched Deezer album and its tracklist for the card popup."""
    artist = str(artist or "").strip()[:180]
    album = str(album or "").strip()[:180]
    if not artist or not album:
        raise HTTPException(status_code=400, detail="artist and album are required")

    def key(value):
        return "".join(char.casefold() for char in str(value or "") if char.isalnum())

    result = {"artist": artist, "album": album, "year": None, "artwork_url": None, "tracks": []}
    try:
        query = urlencode({"q": f'artist:"{artist}" album:"{album}"', "limit": 12})
        response = _EXTERNAL_HTTP.get("https://api.deezer.com/search/album?" + query)
        response.raise_for_status()
        albums = response.json().get("data") or []
        exact = [
            item for item in albums
            if key((item.get("artist") or {}).get("name")) == key(artist)
            and key(item.get("title")) == key(album)
        ]
        if not exact:
            result["message"] = "No exact catalog match was found, so the tracklist is unavailable."
            return result

        match = exact[0]
        release_date = str(match.get("release_date") or "")
        year_text = release_date[:4]
        result.update({
            "matched_artist": (match.get("artist") or {}).get("name"),
            "matched_album": match.get("title"),
            "year": int(year_text) if year_text.isdigit() and 1900 <= int(year_text) <= 2100 else None,
            "artwork_url": (match.get("cover_xl") or match.get("cover_big") or match.get("cover_medium") or "").replace("http://", "https://", 1) or None,
        })
        album_id = match.get("id")
        if not album_id:
            result["message"] = "Album artwork found, but the catalog did not provide a tracklist ID."
            return result

        detail_response = _EXTERNAL_HTTP.get(f"https://api.deezer.com/album/{album_id}")
        detail_response.raise_for_status()
        details = detail_response.json()
        result["tracks"] = [
            {
                "track_number": int(track.get("track_position") or index + 1),
                "title": str(track.get("title") or "").strip(),
                "duration_seconds": int(track.get("duration") or 0),
            }
            for index, track in enumerate(details.get("tracks", {}).get("data") or [])
            if str(track.get("title") or "").strip()
        ]
        if not result["tracks"]:
            result["message"] = "The album was found, but its tracklist is unavailable."
        return result
    except Exception:
        result["message"] = "The album catalog is temporarily unavailable."
        return result


@router.get("/api/artwork")
def album_artwork(artist: str = "", album: str = ""):
    artist = artist.strip()[:180]
    album = album.strip()[:180]
    if not artist and not album:
        raise HTTPException(status_code=400, detail="artist or album is required")

    key = (artist.casefold(), album.casefold())
    now = monotonic()
    cached = _artwork_cache.get(key)
    if cached:
        ttl = _ARTWORK_CACHE_TTL if cached["data"].get("artwork_url") else _ARTWORK_NEGATIVE_CACHE_TTL
        if now - cached["time"] < ttl:
            return cached["data"]

    result = {"artwork_url": None, "image_kind": "album", "source": "Deezer"}
    lookup_failed = False
    try:
        if artist and album:
            query = urlencode({"q": f'artist:"{artist}" album:"{album}"', "limit": 8})
        else:
            query = urlencode({"q": artist or album, "limit": 8})
        endpoint = "https://api.deezer.com/search/album?" + query
        response = _EXTERNAL_HTTP.get(endpoint)
        response.raise_for_status()
        payload = response.json()
        albums = payload.get("data") or []

        def match_score(item):
            candidate_artist = str((item.get("artist") or {}).get("name") or "").casefold()
            candidate_album = str(item.get("title") or "").casefold()
            score = 0
            if artist.casefold() == candidate_artist:
                score += 5
            elif artist and artist.casefold() in candidate_artist:
                score += 2
            if album.casefold() == candidate_album:
                score += 8
            elif album and (album.casefold() in candidate_album or candidate_album in album.casefold()):
                score += 4
            return score

        if albums:
            match = max(albums, key=match_score)
            if match_score(match) >= 9:
                # Prefer Deezer's XL artwork for crisp large cards and high-DPI displays.
                artwork = match.get("cover_xl") or match.get("cover_big") or match.get("cover_medium")
                release_date = str(match.get("release_date") or "")
                year_text = release_date[:4]
                result = {
                    "artwork_url": artwork.replace("http://", "https://", 1) if artwork else None,
                    "image_kind": "album",
                    "source": "Deezer",
                    "matched_artist": (match.get("artist") or {}).get("name"),
                    "matched_album": match.get("title"),
                    "year": int(year_text) if year_text.isdigit() and 1900 <= int(year_text) <= 2100 else None,
                }

        # Do not perform a serialized MusicBrainz lookup here: it rate-limits
        # requests and can delay artwork by several seconds. Deezer release dates
        # are shown when available; missing years must never delay the cover.
        # If the album is not in the catalog, use a matching artist photo instead.
        if not result["artwork_url"] and artist:
            artist_query = urlencode({"q": artist, "limit": 8})
            response = _EXTERNAL_HTTP.get("https://api.deezer.com/search/artist?" + artist_query)
            response.raise_for_status()
            artist_payload = response.json()
            artists = artist_payload.get("data") or []
            exact = next(
                (item for item in artists if str(item.get("name") or "").casefold() == artist.casefold()),
                None,
            )
            if exact:
                # Prefer high-resolution artist portraits; fall back if unavailable.
                photo = exact.get("picture_xl") or exact.get("picture_big") or exact.get("picture_medium")
                if photo:
                    result = {
                        "artwork_url": photo.replace("http://", "https://", 1),
                        "image_kind": "artist",
                        "source": "Deezer",
                        "matched_artist": exact.get("name"),
                        "year": result.get("year"),
                    }
    except Exception:
        # A provider outage must not poison the negative cache for five minutes.
        # Tell the browser this result is transient so it can retry with backoff.
        lookup_failed = True
        result["retryable"] = True

    if not lookup_failed:
        _artwork_cache[key] = {"time": monotonic(), "data": result}
    return result


